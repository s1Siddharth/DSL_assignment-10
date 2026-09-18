"""
OmniShield AI — Analysis Service
Orchestrates the complete activity analysis flow:
Input → Validate → Preprocess → Predict → Anomaly → Risk → Explain → Store → Alert → Return
"""
import logging
from datetime import datetime, timezone
from typing import Any

from flask import current_app

from ..extensions import db
from ..models.activity import Activity
from ..ml.model_manager import model_manager
from ..ml.predict import predict
from ..ml.anomaly import score_anomaly
from .risk import compute_risk_score, classify_severity
from .explanation import generate_explanation
from .alerts import generate_alerts_for_activity

logger = logging.getLogger(__name__)


def analyse_activity(input_data: dict) -> dict[str, Any]:
    """
    Full analysis pipeline for a single network activity input.
    
    Args:
        input_data: dict with optional keys source, destination, protocol,
                    and any feature fields expected by the model.
    
    Returns:
        Full result dict suitable for API response.
    
    Raises:
        RuntimeError: if no model is loaded.
        ValueError: if input is invalid.
    """
    if not model_manager.is_loaded:
        raise RuntimeError(
            "No trained model is available. Please upload a dataset and train a model first."
        )

    feature_names = model_manager.feature_names
    metadata = model_manager.metadata

    # ── 1. Extract network metadata ──────────────────────────────────────────
    source = input_data.get("source", "").strip() or None
    destination = input_data.get("destination", "").strip() or None
    protocol = input_data.get("protocol", "").strip() or None

    # ── 2. Build feature input (only model features) ─────────────────────────
    raw_features = {}
    for feat in feature_names:
        val = input_data.get(feat)
        if val is not None and val != "":
            try:
                raw_features[feat] = float(val)
            except (TypeError, ValueError):
                raw_features[feat] = val   # keep as string for categorical

    # ── 3. Run ML prediction ─────────────────────────────────────────────────
    pred_result = predict(
        raw_input=raw_features,
        model=model_manager.model,
        preprocessor=model_manager.preprocessor,
        label_encoder=model_manager.label_encoder,
        feature_names=feature_names,
    )

    prediction = pred_result["prediction"]
    attack_type = pred_result["attack_type"]
    confidence = pred_result["confidence"]
    class_probabilities = pred_result.get("class_probabilities")

    # ── 4. Anomaly detection (optional) ─────────────────────────────────────
    anomaly_score = None
    if model_manager.anomaly_model is not None:
        try:
            from ..ml.preprocessing import prepare_input_for_prediction
            import pandas as pd
            input_df = prepare_input_for_prediction(raw_features, feature_names)
            X_transformed = model_manager.preprocessor.transform(input_df)
            anomaly_score = score_anomaly(X_transformed, model_manager.anomaly_model)
        except Exception as exc:
            logger.warning("Anomaly scoring failed: %s", exc)

    # ── 5. Risk score + severity ─────────────────────────────────────────────
    risk_score = compute_risk_score(
        prediction=prediction,
        attack_type=attack_type,
        confidence=confidence,
        anomaly_score=anomaly_score,
        raw_features=raw_features,
    )
    severity = classify_severity(risk_score)

    # ── 6. Generate explanation ──────────────────────────────────────────────
    model_feature_importance = metadata.get("feature_importance") or []
    explanation = generate_explanation(
        prediction=prediction,
        attack_type=attack_type,
        confidence=confidence,
        risk_score=risk_score,
        severity=severity,
        anomaly_score=anomaly_score,
        class_probabilities=class_probabilities,
        raw_features=raw_features,
        model_feature_importance=model_feature_importance,
        feature_names=feature_names,
    )

    # ── 7. Store Activity ────────────────────────────────────────────────────
    activity = Activity(
        source=source,
        destination=destination,
        protocol=protocol,
        prediction=prediction,
        attack_type=attack_type,
        confidence=confidence,
        risk_score=risk_score,
        severity=severity,
        anomaly_score=anomaly_score,
    )
    activity.explanation = explanation
    activity.raw_features = raw_features

    db.session.add(activity)
    try:
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.error("Failed to store activity: %s", exc)
        raise RuntimeError("Failed to store activity in database.") from exc

    # ── 8. Generate Alerts ───────────────────────────────────────────────────
    generated_alerts = []
    try:
        alerts = generate_alerts_for_activity(activity)
        generated_alerts = [a.to_dict() for a in alerts]
    except Exception as exc:
        logger.error("Alert generation failed: %s", exc)

    # ── 9. Build result ──────────────────────────────────────────────────────
    return {
        "activity_id": activity.id,
        "timestamp": activity.created_at.isoformat(),
        "prediction": prediction,
        "attack_type": attack_type,
        "confidence": confidence,
        "risk_score": risk_score,
        "severity": severity,
        "anomaly_score": anomaly_score,
        "explanation": explanation,
        "alerts_generated": generated_alerts,
        "model_version": metadata.get("version"),
    }


def validate_analysis_input(data: dict, feature_names: list[str]) -> list[str]:
    """
    Validate the analysis input dict.
    Returns a list of validation error messages (empty = valid).
    """
    errors = []
    if not data:
        errors.append("Request body is empty.")
        return errors

    # Check at least some features are present
    provided_features = [f for f in feature_names if f in data and data[f] != ""]
    if len(provided_features) == 0 and len(feature_names) > 0:
        errors.append(
            f"No model features provided. Expected fields: {feature_names[:5]}{'...' if len(feature_names) > 5 else ''}"
        )

    return errors


def analyse_batch(data_list: list[dict]) -> dict:
    """
    Process a batch of network activities (e.g. from a CSV upload).
    """
    if not model_manager.is_loaded:
        raise RuntimeError("No trained model is available.")

    total_rows = len(data_list)
    results = []
    
    counts = {"normal": 0, "suspicious": 0, "attack": 0}
    alerts_generated = 0
    
    for row in data_list:
        try:
            res = analyse_activity(row)
            results.append(res)
            counts[res["prediction"]] += 1
            alerts_generated += len(res.get("alerts_generated", []))
        except Exception as e:
            logger.warning(f"Failed to analyse row in batch: {e}")
            
    return {
        "total_analyzed": len(results),
        "total_submitted": total_rows,
        "prediction_counts": counts,
        "alerts_generated": alerts_generated,
        "model_version": model_manager.version
    }
