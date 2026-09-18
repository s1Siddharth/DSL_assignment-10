"""
OmniShield AI — Prediction Service
Uses the exact saved preprocessing pipeline from training.
Confidence = max(predict_proba). Never fabricated.
"""
import logging
from typing import Any, Optional

import numpy as np
import pandas as pd

from .preprocessing import prepare_input_for_prediction

logger = logging.getLogger(__name__)


def predict(
    raw_input: dict,
    model,
    preprocessor,
    label_encoder,
    feature_names: list[str],
) -> dict[str, Any]:
    """
    Run a single prediction.

    Args:
        raw_input: dict of {feature_name: value}
        model: trained RandomForestClassifier
        preprocessor: fitted ColumnTransformer
        label_encoder: fitted LabelEncoder
        feature_names: list of expected input feature names

    Returns dict with: prediction, attack_type, confidence, class_probabilities
    """
    # Build input DataFrame with correct columns
    input_df = prepare_input_for_prediction(raw_input, feature_names)

    # Transform using the saved preprocessing pipeline (same as training)
    try:
        X_transformed = preprocessor.transform(input_df)
    except Exception as exc:
        logger.error("Preprocessing transform failed: %s", exc)
        raise ValueError(f"Input preprocessing failed: {exc}") from exc

    # Predict class
    y_pred_encoded = model.predict(X_transformed)
    predicted_label = label_encoder.inverse_transform(y_pred_encoded)[0]

    # Confidence via predict_proba
    confidence = None
    class_probabilities = None
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(X_transformed)[0]
        confidence = float(np.max(proba))
        class_probabilities = {
            str(label_encoder.inverse_transform([i])[0]): round(float(p), 4)
            for i, p in enumerate(proba)
        }

    # Normalise prediction label to standard categories
    prediction, attack_type = _normalise_prediction(str(predicted_label))

    return {
        "prediction": prediction,
        "attack_type": attack_type,
        "raw_label": str(predicted_label),
        "confidence": round(confidence, 4) if confidence is not None else None,
        "class_probabilities": class_probabilities,
    }


def _normalise_prediction(label: str) -> tuple[str, Optional[str]]:
    """
    Map model output label to (prediction, attack_type).
    prediction: "normal" | "attack" | "suspicious"
    attack_type: specific attack name or None
    """
    label_lower = label.lower().strip()

    normal_labels = {"normal", "benign", "legitimate", "safe", "0"}
    suspicious_labels = {"suspicious", "anomaly", "unknown"}

    if label_lower in normal_labels:
        return "normal", None
    if label_lower in suspicious_labels:
        return "suspicious", label_lower
    # Anything else is treated as a known attack type
    return "attack", label_lower
