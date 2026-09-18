"""
OmniShield AI — Real-Time Telemetry Dashboard Service
Computes real-time statistics, threat scores, attack trends, and activity distribution from database.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func

from ..extensions import db
from ..models.activity import Activity
from ..models.alert import Alert, AlertStatus
from ..ml.model_manager import model_manager

logger = logging.getLogger(__name__)


def get_dashboard_data() -> dict[str, Any]:
    """Compute and return all real-time dashboard statistics from the database."""
    total = Activity.query.count()

    normal = Activity.query.filter_by(prediction="normal").count()
    suspicious = Activity.query.filter_by(prediction="suspicious").count()
    attacks = Activity.query.filter_by(prediction="attack").count()
    attack_pct = round((attacks / total) * 100, 1) if total > 0 else 0.0

    security_score = _compute_security_score(total, attacks, suspicious)
    threat_level = _threat_level_from_score(security_score)

    recent_alerts = (
        Alert.query.filter(Alert.status != AlertStatus.RESOLVED)
        .order_by(Alert.created_at.desc())
        .limit(6)
        .all()
    )

    recent_activities = (
        Activity.query.order_by(Activity.created_at.desc())
        .limit(6)
        .all()
    )

    attack_trend = _compute_attack_trend(days=7)
    attack_distribution = _compute_attack_distribution()
    severity_distribution = _compute_severity_distribution()

    return {
        "total_activities": total,
        "normal_count": normal,
        "suspicious_count": suspicious,
        "attack_count": attacks,
        "attack_percentage": attack_pct,
        "security_score": security_score,
        "threat_level": threat_level,
        "recent_alerts": [a.to_dict() for a in recent_alerts],
        "recent_activities": [a.to_dict() for a in recent_activities],
        "attack_trend": attack_trend,
        "attack_distribution": attack_distribution,
        "severity_distribution": severity_distribution,
        "current_model": _get_model_info(),
        "has_data": total > 0,
    }


def _compute_security_score(total: int, attacks: int, suspicious: int) -> int:
    """Compute dynamic security score (0–100) from database state."""
    if total == 0:
        return 100
    penalty = (attacks * 25 + suspicious * 10) / total
    score = int(100 - min(80, penalty * 100))
    return max(10, min(100, score))


def _threat_level_from_score(score: int) -> str:
    if score >= 80:
        return "LOW"
    if score >= 60:
        return "MEDIUM"
    if score >= 40:
        return "HIGH"
    return "CRITICAL"


def _compute_attack_trend(days: int = 7) -> list[dict]:
    """Return daily attack counts for the last N days."""
    result = []
    now = datetime.now(timezone.utc)
    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Activity.query.filter(
            Activity.created_at >= day_start,
            Activity.created_at < day_end,
            Activity.prediction == "attack",
        ).count()
        result.append({
            "date": day_start.strftime("%b %d"),
            "attacks": count,
        })
    return result


def _compute_attack_distribution() -> list[dict]:
    """Return attack type counts from real database records."""
    rows = (
        db.session.query(Activity.attack_type, func.count(Activity.id))
        .filter(Activity.attack_type.isnot(None))
        .group_by(Activity.attack_type)
        .all()
    )
    return [{"attack_type": row[0].upper(), "count": row[1]} for row in rows]


def _compute_severity_distribution() -> list[dict]:
    """Return severity label counts from real database records."""
    rows = (
        db.session.query(Activity.severity, func.count(Activity.id))
        .group_by(Activity.severity)
        .all()
    )
    return [{"severity": row[0], "count": row[1]} for row in rows]


def _get_model_info() -> dict:
    """Return current ML model info from model manager."""
    if not model_manager.is_loaded:
        return {"loaded": False, "version": None, "model_name": None, "accuracy": None, "feature_count": 0}
    meta = model_manager.metadata
    return {
        "loaded": True,
        "version": meta.get("version", "v1.0"),
        "model_name": meta.get("model_name", "RandomForestClassifier"),
        "classes": model_manager.classes,
        "accuracy": meta.get("accuracy", None),
        "feature_count": len(model_manager.feature_names),
    }
