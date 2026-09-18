"""
OmniShield AI — Activity Model
Stores every analysed network event.
"""
import json
from datetime import datetime, timezone
from ..extensions import db


class Activity(db.Model):
    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    # Network metadata
    source = db.Column(db.String(64), nullable=True)
    destination = db.Column(db.String(64), nullable=True)
    protocol = db.Column(db.String(32), nullable=True)

    # ML results
    prediction = db.Column(db.String(32), nullable=False)    # "normal" | "attack" | "suspicious"
    attack_type = db.Column(db.String(64), nullable=True)    # e.g. "dos", "probe", None
    confidence = db.Column(db.Float, nullable=True)          # 0.0–1.0 or None if unavailable
    risk_score = db.Column(db.Float, nullable=False, default=0.0)   # 0–100
    severity = db.Column(db.String(16), nullable=False, default="INFO")
    anomaly_score = db.Column(db.Float, nullable=True)       # 0.0–1.0 normalised, or None

    # Explanation JSON (stored as text)
    _explanation = db.Column("explanation", db.Text, nullable=True)

    # Raw feature values JSON
    _raw_features = db.Column("raw_features", db.Text, nullable=True)

    # Relationships
    alerts = db.relationship("Alert", backref="activity", lazy="dynamic", cascade="all, delete-orphan")

    # ── Properties ─────────────────────────────────────────────────────────

    @property
    def explanation(self):
        if self._explanation:
            try:
                return json.loads(self._explanation)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @explanation.setter
    def explanation(self, value):
        self._explanation = json.dumps(value) if value is not None else None

    @property
    def raw_features(self):
        if self._raw_features:
            try:
                return json.loads(self._raw_features)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    @raw_features.setter
    def raw_features(self, value):
        self._raw_features = json.dumps(value) if value is not None else None

    # ── Serialisation ──────────────────────────────────────────────────────

    def to_dict(self, include_details: bool = False) -> dict:
        data = {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "source": self.source,
            "destination": self.destination,
            "protocol": self.protocol,
            "prediction": self.prediction,
            "attack_type": self.attack_type,
            "confidence": round(self.confidence, 4) if self.confidence is not None else None,
            "risk_score": round(self.risk_score, 2),
            "severity": self.severity,
            "anomaly_score": round(self.anomaly_score, 4) if self.anomaly_score is not None else None,
        }
        if include_details:
            data["explanation"] = self.explanation
            data["raw_features"] = self.raw_features
        return data

    def __repr__(self) -> str:
        return f"<Activity id={self.id} prediction={self.prediction} risk={self.risk_score}>"
