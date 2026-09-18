"""
OmniShield AI — Models Routes
GET /api/model/info
GET /api/model/performance
"""
import logging
from flask import Blueprint, current_app
from ..models.model_run import ModelRun, ModelRunStatus
from ..ml.model_manager import model_manager, load_latest_model_from_db
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
models_bp = Blueprint("models", __name__)


@models_bp.route("/model/info", methods=["GET"])
def model_info():
    if not model_manager.is_loaded:
        load_latest_model_from_db(current_app._get_current_object())
    
    if not model_manager.is_loaded:
        return success_response({"loaded": False, "message": "No trained model available."})
    
    meta = model_manager.metadata
    return success_response({
        "loaded": True,
        "version": meta.get("version"),
        "model_name": meta.get("model_name", "RandomForestClassifier"),
        "classes": model_manager.classes,
        "accuracy": meta.get("accuracy"),
        "f1_score": meta.get("f1_score"),
        "feature_names": model_manager.feature_names,
        "feature_count": len(model_manager.feature_names),
        "training_samples": meta.get("training_samples"),
        "model_run_id": meta.get("model_run_id"),
    })


@models_bp.route("/model/performance", methods=["GET"])
def model_performance():
    if not model_manager.is_loaded:
        load_latest_model_from_db(current_app._get_current_object())

    latest = (
        ModelRun.query.filter_by(status=ModelRunStatus.COMPLETED)
        .order_by(ModelRun.created_at.desc())
        .first()
    )
    if latest is None:
        return success_response({"has_model": False, "message": "No completed model runs found."})
    return success_response({"has_model": True, **latest.to_dict(include_details=True)})


@models_bp.route("/models", methods=["GET"])
def list_models():
    runs = ModelRun.query.order_by(ModelRun.created_at.desc()).all()
    return success_response({"models": [r.to_dict() for r in runs]})


@models_bp.route("/model/status/<int:run_id>", methods=["GET"])
def model_status(run_id: int):
    run = ModelRun.query.get(run_id)
    if run is None:
        return error_response("NOT_FOUND", f"ModelRun {run_id} not found.", 404)
    return success_response(run.to_dict())
