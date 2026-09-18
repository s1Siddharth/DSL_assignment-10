"""
OmniShield AI — Reports Service
Generates reports from actual database and model data.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from ..extensions import db
from ..models.activity import Activity
from ..models.alert import Alert, AlertStatus
from ..models.model_run import ModelRun, ModelRunStatus
from ..ml.model_manager import model_manager

logger = logging.getLogger(__name__)


def generate_report(report_type: str = "summary") -> dict[str, Any]:
    """
    Generate a report dict from actual database and model state.
    report_type: "summary" | "detailed"
    """
    generated_at = datetime.now(timezone.utc).isoformat()
    total_activities = Activity.query.count()
    normal = Activity.query.filter_by(prediction="normal").count()
    suspicious = Activity.query.filter_by(prediction="suspicious").count()
    attacks = Activity.query.filter_by(prediction="attack").count()

    total_alerts = Alert.query.count()
    open_alerts = Alert.query.filter(Alert.status == AlertStatus.NEW).count()
    resolved_alerts = Alert.query.filter(Alert.status == AlertStatus.RESOLVED).count()

    # Attack breakdown
    attack_rows = (
        db.session.query(Activity.attack_type, func.count(Activity.id))
        .filter(Activity.prediction == "attack", Activity.attack_type.isnot(None))
        .group_by(Activity.attack_type)
        .all()
    )
    attack_breakdown = {row[0]: row[1] for row in attack_rows}

    # Severity breakdown
    severity_rows = (
        db.session.query(Activity.severity, func.count(Activity.id))
        .group_by(Activity.severity)
        .all()
    )
    severity_breakdown = {row[0]: row[1] for row in severity_rows}

    # Average risk score
    avg_risk = db.session.query(func.avg(Activity.risk_score)).scalar()
    max_risk = db.session.query(func.max(Activity.risk_score)).scalar()

    # Current model info
    model_info = None
    latest_run = (
        ModelRun.query.filter_by(status=ModelRunStatus.COMPLETED)
        .order_by(ModelRun.created_at.desc())
        .first()
    )
    if latest_run:
        model_info = {
            "model_name": latest_run.model_name,
            "version": latest_run.version,
            "accuracy": latest_run.accuracy,
            "f1_score": latest_run.f1_score,
            "classes": latest_run.classes,
            "training_samples": latest_run.training_samples,
        }

    report = {
        "generated_at": generated_at,
        "report_type": report_type,
        "summary": {
            "total_activities": total_activities,
            "normal": normal,
            "suspicious": suspicious,
            "attacks": attacks,
            "attack_percentage": round((attacks / total_activities * 100), 1) if total_activities > 0 else 0,
        },
        "alerts": {
            "total": total_alerts,
            "open": open_alerts,
            "resolved": resolved_alerts,
        },
        "risk": {
            "average": round(avg_risk, 2) if avg_risk else None,
            "maximum": round(max_risk, 2) if max_risk else None,
        },
        "attack_breakdown": attack_breakdown,
        "severity_breakdown": severity_breakdown,
        "model": model_info,
    }

    if report_type == "detailed":
        # Include recent activities and alerts
        recent_activities = (
            Activity.query.order_by(Activity.created_at.desc()).limit(50).all()
        )
        recent_alerts = (
            Alert.query.order_by(Alert.created_at.desc()).limit(20).all()
        )
        report["recent_activities"] = [a.to_dict(include_details=False) for a in recent_activities]
        report["recent_alerts"] = [a.to_dict() for a in recent_alerts]

    return report
