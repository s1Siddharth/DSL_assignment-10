"""
OmniShield AI — Model Manager (singleton)
Loads and caches the current trained model + preprocessing pipeline.
Exposes model metadata (feature names, classes, version).
"""
import json
import logging
import os
from typing import Any, Optional

import joblib

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Singleton that holds the currently active model artifacts.
    Thread-safe for read access (no mutation after load).
    """

    _instance: Optional["ModelManager"] = None

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._model = None
        self._preprocessor = None
        self._label_encoder = None
        self._anomaly_model = None
        self._feature_names: list[str] = []
        self._metadata: dict[str, Any] = {}
        self._initialised = True

    # ── Public API ──────────────────────────────────────────────────────────

    def load(
        self,
        model_path: str,
        preprocessing_path: str,
        label_encoder_path: str,
        feature_names: list[str],
        metadata: dict,
        anomaly_model_path: Optional[str] = None,
    ) -> None:
        """Load model artifacts from disk. Raises on failure."""
        logger.info("Loading model from: %s", model_path)
        self._model = joblib.load(model_path)
        self._preprocessor = joblib.load(preprocessing_path)
        self._label_encoder = joblib.load(label_encoder_path)
        self._feature_names = feature_names
        self._metadata = metadata

        if anomaly_model_path and os.path.exists(anomaly_model_path):
            self._anomaly_model = joblib.load(anomaly_model_path)
            logger.info("Anomaly model loaded.")
        else:
            self._anomaly_model = None

        logger.info(
            "Model loaded — version=%s classes=%s features=%d",
            metadata.get("version", "?"),
            metadata.get("classes", []),
            len(feature_names),
        )

    def reset(self) -> None:
        """Unload all model artifacts (e.g., after retraining)."""
        self._model = None
        self._preprocessor = None
        self._label_encoder = None
        self._anomaly_model = None
        self._feature_names = []
        self._metadata = {}
        logger.info("ModelManager reset.")

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._preprocessor is not None

    @property
    def model(self):
        return self._model

    @property
    def preprocessor(self):
        return self._preprocessor

    @property
    def label_encoder(self):
        return self._label_encoder

    @property
    def anomaly_model(self):
        return self._anomaly_model

    @property
    def feature_names(self) -> list[str]:
        return self._feature_names

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def classes(self) -> list[str]:
        if self._label_encoder is not None:
            return self._label_encoder.classes_.tolist()
        return self._metadata.get("classes", [])

    @property
    def version(self) -> Optional[str]:
        return self._metadata.get("version")


# Module-level singleton
model_manager = ModelManager()


def load_latest_model_from_db(app) -> bool:
    """
    Query the DB for the latest completed ModelRun and load it.
    Called at app startup or after training.
    Returns True if a model was loaded, False if none available.
    """
    from ..models.model_run import ModelRun, ModelRunStatus

    with app.app_context():
        latest = (
            ModelRun.query.filter_by(status=ModelRunStatus.COMPLETED)
            .order_by(ModelRun.created_at.desc())
            .first()
        )
        if latest is None:
            logger.info("No completed model found in database.")
            return False

        if not latest.model_path or not os.path.exists(latest.model_path):
            logger.warning("Model file missing: %s", latest.model_path)
            return False

        preprocessing_path = latest.preprocessing_path
        if not preprocessing_path or not os.path.exists(preprocessing_path):
            logger.warning("Preprocessing file missing: %s", preprocessing_path)
            return False

        # Derive label encoder path from model path convention
        label_encoder_path = latest.model_path.replace("rf_model_", "label_encoder_")
        if not os.path.exists(label_encoder_path):
            logger.warning("Label encoder file missing: %s", label_encoder_path)
            return False

        feature_names = latest.feature_names or []
        metadata = {
            "version": latest.version,
            "model_name": latest.model_name,
            "classes": latest.classes or [],
            "accuracy": latest.accuracy,
            "f1_score": latest.f1_score,
            "training_samples": latest.training_samples,
            "feature_names": feature_names,
            "model_run_id": latest.id,
        }

        try:
            model_manager.load(
                model_path=latest.model_path,
                preprocessing_path=preprocessing_path,
                label_encoder_path=label_encoder_path,
                feature_names=feature_names,
                metadata=metadata,
            )
            return True
        except Exception as exc:
            logger.error("Failed to load model: %s", exc)
            return False
