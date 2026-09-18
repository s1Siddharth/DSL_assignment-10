"""
OmniShield AI — Datasets Routes
POST /api/dataset/upload
GET  /api/datasets
POST /api/dataset/train
"""
import hashlib
import logging
import os
import threading
from datetime import datetime, timezone
from werkzeug.utils import secure_filename

from flask import Blueprint, current_app, request

from ..extensions import db
from ..models.dataset import Dataset, DatasetStatus, TrainingStatus
from ..models.model_run import ModelRun, ModelRunStatus
from ..ml.model_manager import model_manager, load_latest_model_from_db
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
datasets_bp = Blueprint("datasets", __name__)


def _allowed_file(filename: str, allowed_extensions: set) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def _file_hash(filepath: str) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


@datasets_bp.route("/dataset/upload", methods=["POST"])
def upload_dataset():
    if "file" not in request.files:
        return error_response("VALIDATION_ERROR", "No file provided in request.", 400)

    file = request.files["file"]
    if not file.filename:
        return error_response("VALIDATION_ERROR", "File has no filename.", 400)

    allowed = current_app.config.get("ALLOWED_EXTENSIONS", {"csv"})
    if not _allowed_file(file.filename, allowed):
        return error_response(
            "VALIDATION_ERROR",
            f"Invalid file type. Only {', '.join(allowed)} files are allowed.",
            400,
        )

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    os.makedirs(upload_folder, exist_ok=True)

    original_name = secure_filename(file.filename)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    stored_name = f"{ts}_{original_name}"
    filepath = os.path.join(upload_folder, stored_name)
    file.save(filepath)

    file_size = os.path.getsize(filepath)
    file_hash = _file_hash(filepath)

    # Check for duplicate
    existing = Dataset.query.filter_by(dataset_hash=file_hash).first()
    if existing:
        os.remove(filepath)
        return error_response(
            "CONFLICT",
            f"This dataset has already been uploaded (id={existing.id}).",
            409,
        )

    # Parse CSV to get shape
    try:
        import pandas as pd
        df = pd.read_csv(filepath, nrows=5000)  # sample for inspection
        row_count = len(pd.read_csv(filepath, usecols=[0]))
        col_count = len(df.columns)
        columns = df.columns.tolist()
        sample_rows = df.head(5).to_dict(orient="records")
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
    except Exception as exc:
        os.remove(filepath)
        return error_response("VALIDATION_ERROR", f"Failed to parse CSV: {exc}", 400)

    dataset = Dataset(
        filename=stored_name,
        original_filename=original_name,
        row_count=row_count,
        column_count=col_count,
        file_size=file_size,
        dataset_hash=file_hash,
        status=DatasetStatus.UPLOADED,
        training_status=TrainingStatus.PENDING,
    )
    db.session.add(dataset)
    db.session.commit()

    return success_response({
        "dataset_id": dataset.id,
        "filename": original_name,
        "row_count": row_count,
        "column_count": col_count,
        "columns": columns,
        "dtypes": dtypes,
        "sample_rows": sample_rows,
        "file_size": file_size,
    }, "Dataset uploaded successfully.", 201)


@datasets_bp.route("/datasets", methods=["GET"])
def list_datasets():
    datasets = Dataset.query.order_by(Dataset.uploaded_at.desc()).all()
    return success_response({"datasets": [d.to_dict() for d in datasets]})


@datasets_bp.route("/dataset/train", methods=["POST"])
def train_dataset():
    data = request.get_json(silent=True) or {}
    dataset_id = data.get("dataset_id")
    target_column = data.get("target_column", "").strip()

    if not dataset_id:
        return error_response("VALIDATION_ERROR", "Field 'dataset_id' is required.", 400)
    if not target_column:
        return error_response("VALIDATION_ERROR", "Field 'target_column' is required.", 400)

    dataset = Dataset.query.get(dataset_id)
    if dataset is None:
        return error_response("NOT_FOUND", f"Dataset {dataset_id} not found.", 404)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    csv_path = os.path.join(upload_folder, dataset.filename)
    if not os.path.exists(csv_path):
        return error_response("NOT_FOUND", "Dataset file not found on disk.", 404)

    # Check if already training
    if dataset.training_status == TrainingStatus.TRAINING:
        return error_response("CONFLICT", "Dataset is already being trained.", 409)

    # Update dataset
    dataset.target_column = target_column
    dataset.training_status = TrainingStatus.TRAINING

    # Create a ModelRun placeholder
    import uuid
    version = f"v{ModelRun.query.count() + 1}_{uuid.uuid4().hex[:6]}"
    model_run = ModelRun(
        model_name="RandomForestClassifier",
        version=version,
        dataset_id=dataset.id,
        status=ModelRunStatus.TRAINING,
    )
    db.session.add(model_run)
    db.session.commit()

    # Run training in background thread
    app = current_app._get_current_object()
    thread = threading.Thread(
        target=_run_training,
        args=(app, dataset.id, model_run.id, csv_path, target_column),
        daemon=True,
    )
    thread.start()

    return success_response(
        {"model_run_id": model_run.id, "version": version},
        "Training started. Check model status for progress.",
        202,
    )


def _run_training(app, dataset_id: int, model_run_id: int, csv_path: str, target_column: str):
    """Background training task."""
    with app.app_context():
        from ..ml.train import train_model

        model_run = ModelRun.query.get(model_run_id)
        dataset = Dataset.query.get(dataset_id)

        try:
            cfg = app.config
            result = train_model(
                csv_path=csv_path,
                target_column=target_column,
                model_folder=cfg["MODEL_FOLDER"],
                metadata_folder=cfg["MODEL_METADATA_FOLDER"],
                n_estimators=cfg.get("RF_N_ESTIMATORS", 100),
                test_size=cfg.get("TRAIN_TEST_SPLIT", 0.2),
                random_state=cfg.get("RANDOM_STATE", 42),
                min_samples_per_class=cfg.get("MIN_SAMPLES_PER_CLASS", 5),
            )

            # Update ModelRun with results
            model_run.version = result["version"]
            model_run.model_path = result["model_path"]
            model_run.preprocessing_path = result["preprocessing_path"]
            model_run.training_samples = result["training_samples"]
            model_run.testing_samples = result["testing_samples"]
            model_run.accuracy = result["accuracy"]
            model_run.precision = result["precision"]
            model_run.recall = result["recall"]
            model_run.f1_score = result["f1_score"]
            model_run.classes = result["classes"]
            model_run.class_metrics = result.get("class_metrics")
            model_run.confusion_matrix = result.get("confusion_matrix")
            model_run.feature_importance = result.get("feature_importance")
            model_run.feature_names = result.get("feature_names")
            model_run.status = ModelRunStatus.COMPLETED

            dataset.training_status = TrainingStatus.COMPLETED
            dataset.status = DatasetStatus.VALIDATED
            db.session.commit()

            # Load the newly trained model
            load_latest_model_from_db(app)
            logger.info("Training completed: version=%s", result["version"])

        except Exception as exc:
            logger.exception("Training failed")
            if model_run:
                model_run.status = ModelRunStatus.FAILED
                model_run.error_message = str(exc)
            if dataset:
                dataset.training_status = TrainingStatus.FAILED
                dataset.validation_error = str(exc)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
