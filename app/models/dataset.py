"""
OmniShield AI — Dataset Model
Tracks uploaded CSV datasets and their training state.
"""
import enum
from datetime import datetime, timezone
from ..extensions import db


class DatasetStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    VALIDATED = "VALIDATED"
    INVALID = "INVALID"


class TrainingStatus(str, enum.Enum):
    PENDING = "PENDING"
    TRAINING = "TRAINING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Dataset(db.Model):
    __tablename__ = "datasets"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    row_count = db.Column(db.Integer, nullable=True)
    column_count = db.Column(db.Integer, nullable=True)
    target_column = db.Column(db.String(128), nullable=True)
    status = db.Column(
        db.Enum(DatasetStatus),
        nullable=False,
        default=DatasetStatus.UPLOADED,
    )
    training_status = db.Column(
        db.Enum(TrainingStatus),
        nullable=True,
        default=TrainingStatus.PENDING,
    )
    file_size = db.Column(db.Integer, nullable=True)   # bytes
    dataset_hash = db.Column(db.String(64), nullable=True, unique=True)
    validation_error = db.Column(db.Text, nullable=True)

    # Relationships
    model_runs = db.relationship("ModelRun", backref="dataset", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.original_filename or self.filename,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "target_column": self.target_column,
            "status": self.status.value if self.status else None,
            "training_status": self.training_status.value if self.training_status else None,
            "file_size": self.file_size,
            "validation_error": self.validation_error,
        }

    def __repr__(self) -> str:
        return f"<Dataset id={self.id} filename={self.filename} status={self.status}>"
