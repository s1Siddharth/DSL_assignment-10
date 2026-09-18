"""
OmniShield AI — Analytics Route
GET /api/analytics
"""
import logging
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request
from sqlalchemy import func
from ..extensions import db
from ..models.activity import Activity
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics", methods=["GET"])
def analytics():
    try:
        days = min(90, max(1, request.args.get("days", 30, type=int)))
        since = datetime.now(timezone.utc) - timedelta(days=days)

        total = Activity.query.filter(Activity.created_at >= since).count()

        # Activity distribution (normal/suspicious/attack)
        dist_rows = (
            db.session.query(Activity.prediction, func.count(Activity.id))
            .filter(Activity.created_at >= since)
            .group_by(Activity.prediction)
            .all()
        )
        activity_distribution = [{"label": r[0], "count": r[1]} for r in dist_rows]

        # Attack type distribution
        attack_rows = (
            db.session.query(Activity.attack_type, func.count(Activity.id))
            .filter(Activity.created_at >= since, Activity.prediction == "attack", Activity.attack_type.isnot(None))
            .group_by(Activity.attack_type)
            .all()
        )
        attack_distribution = [{"attack_type": r[0], "count": r[1]} for r in attack_rows]

        # Daily trend
        trend = []
        for i in range(days - 1, -1, -1):
            day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            attacks = Activity.query.filter(
                Activity.created_at >= day_start,
                Activity.created_at < day_end,
                Activity.prediction == "attack",
            ).count()
            normal = Activity.query.filter(
                Activity.created_at >= day_start,
                Activity.created_at < day_end,
                Activity.prediction == "normal",
            ).count()
            trend.append({"date": day_start.strftime("%Y-%m-%d"), "attacks": attacks, "normal": normal})

        # Severity distribution
        severity_rows = (
            db.session.query(Activity.severity, func.count(Activity.id))
            .filter(Activity.created_at >= since)
            .group_by(Activity.severity)
            .all()
        )
        severity_distribution = [{"severity": r[0], "count": r[1]} for r in severity_rows]

        # Risk distribution (bucketed)
        risk_buckets = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
        activities = Activity.query.filter(Activity.created_at >= since).with_entities(Activity.risk_score).all()
        for (risk,) in activities:
            if risk is None:
                continue
            if risk <= 20:
                risk_buckets["0-20"] += 1
            elif risk <= 40:
                risk_buckets["21-40"] += 1
            elif risk <= 60:
                risk_buckets["41-60"] += 1
            elif risk <= 80:
                risk_buckets["61-80"] += 1
            else:
                risk_buckets["81-100"] += 1
        risk_distribution = [{"range": k, "count": v} for k, v in risk_buckets.items()]

        return success_response({
            "period_days": days,
            "total_in_period": total,
            "activity_distribution": activity_distribution,
            "attack_distribution": attack_distribution,
            "attack_trend": trend,
            "severity_distribution": severity_distribution,
            "risk_distribution": risk_distribution,
            "has_data": total > 0,
        })

    except Exception:
        logger.exception("Analytics error")
        return error_response("INTERNAL_ERROR", "Failed to compute analytics.", 500)
