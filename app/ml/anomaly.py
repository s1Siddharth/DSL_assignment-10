"""
OmniShield AI — Anomaly Detection (Isolation Forest)
Complements classification. NOT presented as a known attack category.
"""
import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


def train_anomaly_detector(
    X_train: np.ndarray,
    contamination: float = 0.1,
    random_state: int = 42,
) -> IsolationForest:
    """
    Train an Isolation Forest on the training feature matrix.
    contamination: expected proportion of outliers in training data.
    """
    iso = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1,
    )
    iso.fit(X_train)
    logger.info("Isolation Forest trained (contamination=%.2f).", contamination)
    return iso


def score_anomaly(
    X_transformed: np.ndarray,
    anomaly_model: IsolationForest,
) -> float:
    """
    Compute a normalised anomaly score in [0, 1].
    Isolation Forest returns raw scores where more negative = more anomalous.
    We normalise to [0, 1] where 1 = most anomalous.

    Returns: float in [0, 1]
    """
    raw_score = anomaly_model.score_samples(X_transformed)[0]  # negative of anomaly score
    # score_samples returns the mean anomaly score of the input samples.
    # Typical range: roughly [-0.5, 0.5] but can vary.
    # Map to [0,1]: anomalous → high score
    # We clip and normalise relative to the decision function offset
    decision = anomaly_model.decision_function(X_transformed)[0]
    # decision < 0 means outlier, > 0 means inlier
    # Sigmoid-like normalisation
    normalised = float(1.0 / (1.0 + np.exp(5.0 * decision)))
    return round(max(0.0, min(1.0, normalised)), 4)


def is_anomalous(anomaly_score: float, threshold: float = 0.7) -> bool:
    """Return True if the normalised anomaly score exceeds the threshold."""
    return anomaly_score >= threshold
