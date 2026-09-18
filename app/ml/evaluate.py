"""
OmniShield AI — Model Evaluation
Computes accuracy, precision, recall, F1, confusion matrix, feature importance.
"""
import logging
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)


def evaluate_model(
    model,
    X_test: np.ndarray,
    y_test: np.ndarray,
    label_encoder,
    feature_names: list[str],
) -> dict[str, Any]:
    """
    Evaluate a trained classifier. Returns a dict with all metrics.
    """
    y_pred = model.predict(X_test)
    classes = label_encoder.classes_.tolist()

    # Overall metrics (weighted average)
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(
        precision_score(y_test, y_pred, average="weighted", zero_division=0)
    )
    recall = float(
        recall_score(y_test, y_pred, average="weighted", zero_division=0)
    )
    f1 = float(
        f1_score(y_test, y_pred, average="weighted", zero_division=0)
    )

    # Per-class metrics
    report = classification_report(
        y_test,
        y_pred,
        labels=list(range(len(classes))),
        target_names=classes,
        output_dict=True,
        zero_division=0,
    )
    class_metrics = {
        cls: {
            "precision": round(report[cls]["precision"], 4),
            "recall": round(report[cls]["recall"], 4),
            "f1_score": round(report[cls]["f1-score"], 4),
            "support": int(report[cls]["support"]),
        }
        for cls in classes
        if cls in report
    }

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred, labels=list(range(len(classes)))).tolist()

    # Feature importance
    feature_importance = _extract_feature_importance(model, feature_names)

    logger.info(
        "Evaluation — accuracy=%.4f precision=%.4f recall=%.4f f1=%.4f",
        accuracy, precision, recall, f1,
    )

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "classes": classes,
        "class_metrics": class_metrics,
        "confusion_matrix": cm,
        "feature_importance": feature_importance,
    }


def _extract_feature_importance(model, feature_names: list[str]) -> list[dict]:
    """Extract and sort feature importances from the model."""
    try:
        importances = model.feature_importances_
        # Align with available feature names (after preprocessing may expand)
        n = min(len(importances), len(feature_names))
        importance_pairs = sorted(
            zip(feature_names[:n], importances[:n].tolist()),
            key=lambda x: x[1],
            reverse=True,
        )
        return [
            {"feature": feat, "importance": round(imp, 6)}
            for feat, imp in importance_pairs
        ]
    except AttributeError:
        logger.warning("Model does not support feature_importances_.")
        return []
