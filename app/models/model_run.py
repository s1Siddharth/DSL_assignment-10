"""
OmniShield AI — ModelRun Model
Stores training results, metrics, and model file reference.
"""
import json
import enum
from datetime import datetime, timezone
from ..extensions import db


class ModelRunStatus(str, enum.Enum):
    TRAINING = "TRAINING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ModelRun(db.Model):
    __tablename__ = "model_runs"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(128), nullable=False, default="RandomForestClassifier")
    version = db.Column(db.String(32), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    dataset_id = db.Column(
        db.Integer,
        db.ForeignKey("datasets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Training statistics
    training_samples = db.Column(db.Integer, nullable=True)
    testing_samples = db.Column(db.Integer, nullable=True)

    # Evaluation metrics
    accuracy = db.Column(db.Float, nullable=True)
    precision = db.Column(db.Float, nullable=True)
    recall = db.Column(db.Float, nullable=True)
    f1_score = db.Column(db.Float, nullable=True)

    # JSON fields for detailed metrics
    _classes = db.Column("classes", db.Text, nullable=True)
    _class_metrics = db.Column("class_metrics", db.Text, nullable=True)
    _confusion_matrix = db.Column("confusion_matrix", db.Text, nullable=True)
    _feature_importance = db.Column("feature_importance", db.Text, nullable=True)
    _feature_names = db.Column("feature_names", db.Text, nullable=True)

    # File paths
    model_path = db.Column(db.String(512), nullable=True)
    preprocessing_path = db.Column(db.String(512), nullable=True)
    metadata_path = db.Column(db.String(512), nullable=True)

    status = db.Column(
        db.Enum(ModelRunStatus),
        nullable=False,
        default=ModelRunStatus.TRAINING,
    )
    error_message = db.Column(db.Text, nullable=True)

    # ── JSON properties ─────────────────────────────────────────────────────

    def _get_json(self, field):
        if field:
            try:
                return json.loads(field)
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def _set_json(self, value):
        return json.dumps(value) if value is not None else None

    @property
    def classes(self):
        return self._get_json(self._classes)

    @classes.setter
    def classes(self, value):
        self._classes = self._set_json(value)

    @property
    def class_metrics(self):
        return self._get_json(self._class_metrics)

    @class_metrics.setter
    def class_metrics(self, value):
        self._class_metrics = self._set_json(value)

    @property
    def confusion_matrix(self):
        return self._get_json(self._confusion_matrix)

    @confusion_matrix.setter
    def confusion_matrix(self, value):
        self._confusion_matrix = self._set_json(value)

    @property
    def feature_importance(self):
        return self._get_json(self._feature_importance)

    @feature_importance.setter
    def feature_importance(self, value):
        self._feature_importance = self._set_json(value)

    @property
    def feature_names(self):
        return self._get_json(self._feature_names)

    @feature_names.setter
    def feature_names(self, value):
        self._feature_names = self._set_json(value)

    # ── Serialisation ───────────────────────────────────────────────────────

    def to_dict(self, include_details: bool = False) -> dict:
        data = {
            "id": self.id,
            "model_name": self.model_name,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "dataset_id": self.dataset_id,
            "training_samples": self.training_samples,
            "testing_samples": self.testing_samples,
            "accuracy": round(self.accuracy, 4) if self.accuracy is not None else None,
            "precision": round(self.precision, 4) if self.precision is not None else None,
            "recall": round(self.recall, 4) if self.recall is not None else None,
            "f1_score": round(self.f1_score, 4) if self.f1_score is not None else None,
            "classes": self.classes,
            "status": self.status.value if self.status else None,
            "error_message": self.error_message,
        }
        if include_details:
            data["class_metrics"] = self.class_metrics
            data["confusion_matrix"] = self.confusion_matrix
            data["feature_importance"] = self.feature_importance
            data["feature_names"] = self.feature_names
        return data

    def __repr__(self) -> str:
        return f"<ModelRun id={self.id} version={self.version} status={self.status}>"
