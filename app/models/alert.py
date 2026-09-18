"""
OmniShield AI — Alert Model
Alerts generated from real events via deterministic rules.
"""
import enum
from datetime import datetime, timezone
from ..extensions import db


class AlertStatus(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    activity_id = db.Column(
        db.Integer,
        db.ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(16), nullable=False, default="LOW")
    risk_score = db.Column(db.Float, nullable=True)
    status = db.Column(
        db.Enum(AlertStatus),
        nullable=False,
        default=AlertStatus.NEW,
        index=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "activity_id": self.activity_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "risk_score": round(self.risk_score, 2) if self.risk_score is not None else None,
            "status": self.status.value if self.status else AlertStatus.NEW.value,
        }

    def __repr__(self) -> str:
        return f"<Alert id={self.id} severity={self.severity} status={self.status}>"
