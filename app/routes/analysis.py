"""
OmniShield AI — Analysis Route
POST /api/analyze
"""
import logging
from flask import Blueprint, request
from ..services.analysis import analyse_activity, validate_analysis_input, analyse_batch
from ..ml.model_manager import model_manager
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True)
    if not data:
        return error_response("INVALID_REQUEST", "Request body must be JSON.", 400)

    # Validate input
    feature_names = model_manager.feature_names
    errors = validate_analysis_input(data, feature_names)
    if errors:
        return error_response("VALIDATION_ERROR", " ".join(errors), 422)

    try:
        result = analyse_activity(data)
        return success_response(result, "Activity analysed successfully.")
    except RuntimeError as exc:
        return error_response("MODEL_UNAVAILABLE", str(exc), 503)
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 422)
    except Exception as exc:
        logger.exception("Analysis error")
        return error_response("INTERNAL_ERROR", "Analysis failed unexpectedly.", 500)


@analysis_bp.route("/model/features", methods=["GET"])
def model_features():
    """Return the feature names required by the current model."""
    if not model_manager.is_loaded:
        return success_response({"features": [], "model_loaded": False})
    return success_response({
        "features": model_manager.feature_names,
        "model_loaded": True,
        "classes": model_manager.classes,
        "version": model_manager.version,
    })


import pandas as pd
from werkzeug.utils import secure_filename

@analysis_bp.route("/analyze/batch", methods=["POST"])
def analyze_batch():
    if "file" not in request.files:
        return error_response("MISSING_FILE", "No file part in the request.", 400)
    
    file = request.files["file"]
    if file.filename == "":
        return error_response("NO_FILE_SELECTED", "No selected file.", 400)
        
    if not file.filename.endswith(".csv"):
        return error_response("INVALID_FILE_TYPE", "Only CSV files are supported.", 400)

    try:
        df = pd.read_csv(file)
        # Convert NaN to None for dict processing
        df = df.where(pd.notnull(df), None)
        data_list = df.to_dict(orient="records")
        
        if not data_list:
            return error_response("EMPTY_FILE", "The uploaded CSV is empty.", 400)
            
        # Limit to 5000 rows for sync batch analysis to prevent timeout
        if len(data_list) > 5000:
            return error_response("FILE_TOO_LARGE", "Batch analysis is limited to 5000 rows at a time.", 400)
            
        result = analyse_batch(data_list)
        return success_response(result, "Batch analysis completed successfully.")
        
    except pd.errors.EmptyDataError:
        return error_response("EMPTY_FILE", "The uploaded CSV is empty or malformed.", 400)
    except RuntimeError as exc:
        return error_response("MODEL_UNAVAILABLE", str(exc), 503)
    except Exception as exc:
        logger.exception("Batch analysis error")
        return error_response("INTERNAL_ERROR", "Batch analysis failed.", 500)
