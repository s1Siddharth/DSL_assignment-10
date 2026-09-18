"""
OmniShield AI — Alert Service
Generates alerts from real events using deterministic rules.
No hardcoded alert cards.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from flask import current_app

from ..extensions import db
from ..models.alert import Alert, AlertStatus
from ..models.activity import Activity

logger = logging.getLogger(__name__)


def generate_alerts_for_activity(activity: Activity) -> list[Alert]:
    """
    Evaluate an activity against deterministic alert rules.
    Creates and persists Alert records as needed.
    Returns the list of created alerts.
    """
    cfg = current_app.config
    created_alerts = []

    # ── Rule 1: Attack detected ──────────────────────────────────────────────
    if cfg.get("ALERT_ON_ATTACK", True) and activity.prediction == "attack":
        alert = _create_alert(
            activity=activity,
            title=f"Attack Detected: {(activity.attack_type or 'Unknown').upper()}",
            message=(
                f"A network attack of type '{(activity.attack_type or 'unknown').upper()}' was detected "
                f"from {activity.source or 'unknown source'} to {activity.destination or 'unknown destination'}. "
                f"Risk score: {activity.risk_score}/100."
            ),
            severity=activity.severity,
        )
        created_alerts.append(alert)

    # ── Rule 2: High/Critical risk (even if not a known attack) ─────────────
    elif activity.risk_score >= cfg.get("ALERT_RISK_CRITICAL_THRESHOLD", 80):
        alert = _create_alert(
            activity=activity,
            title="Critical Risk Activity Detected",
            message=(
                f"Network activity with critical risk score ({activity.risk_score}/100) detected. "
                f"Classification: {activity.prediction}. Immediate review required."
            ),
            severity="CRITICAL",
        )
        created_alerts.append(alert)

    elif activity.risk_score >= cfg.get("ALERT_RISK_HIGH_THRESHOLD", 60):
        alert = _create_alert(
            activity=activity,
            title="High Risk Activity Detected",
            message=(
                f"Network activity with high risk score ({activity.risk_score}/100) detected. "
                f"Classification: {activity.prediction}. Review recommended."
            ),
            severity="HIGH",
        )
        created_alerts.append(alert)

    # ── Rule 3: Strong anomaly ────────────────────────────────────────────────
    anomaly_threshold = cfg.get("ALERT_ANOMALY_THRESHOLD", 0.7)
    if (
        activity.anomaly_score is not None
        and activity.anomaly_score >= anomaly_threshold
        and activity.prediction == "normal"   # Only alert if classifier missed it
    ):
        alert = _create_alert(
            activity=activity,
            title="Anomalous Network Behaviour",
            message=(
                f"Unusual network behaviour detected (anomaly score: {activity.anomaly_score:.3f}). "
                "The activity was classified as normal but deviates significantly from baseline."
            ),
            severity="MEDIUM",
        )
        created_alerts.append(alert)

    # ── Rule 4: Repeated suspicious activity ─────────────────────────────────
    repeated_alert = _check_repeated_suspicious(activity, cfg)
    if repeated_alert:
        created_alerts.append(repeated_alert)

    # Commit all created alerts
    if created_alerts:
        try:
            db.session.add_all(created_alerts)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.error("Failed to save alerts: %s", exc)
            return []

    return created_alerts


def _create_alert(
    activity: Activity,
    title: str,
    message: str,
    severity: str,
) -> Alert:
    """Construct an Alert linked to an Activity."""
    return Alert(
        activity_id=activity.id,
        title=title,
        message=message,
        severity=severity,
        risk_score=activity.risk_score,
        status=AlertStatus.NEW,
    )


def _check_repeated_suspicious(activity: Activity, cfg: dict) -> Optional[Alert]:
    """
    Check if there have been N+ suspicious events from the same source
    within the configured time window. Returns an alert or None.
    """
    if activity.prediction not in ("attack", "suspicious"):
        return None
    if not activity.source:
        return None

    window_minutes = cfg.get("ALERT_REPEATED_WINDOW_MINUTES", 10)
    threshold_count = cfg.get("ALERT_REPEATED_COUNT", 3)
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    count = (
        Activity.query.filter(
            Activity.source == activity.source,
            Activity.prediction.in_(["attack", "suspicious"]),
            Activity.created_at >= since,
            Activity.id != activity.id,
        )
        .count()
    )

    if count >= threshold_count - 1:
        # Check we haven't already issued a repeated alert recently
        recent_repeated = Alert.query.filter(
            Alert.title.like(f"%Repeated%{activity.source}%"),
            Alert.created_at >= since,
        ).first()
        if recent_repeated:
            return None

        return Alert(
            activity_id=activity.id,
            title=f"Repeated Suspicious Activity from {activity.source}",
            message=(
                f"Source IP {activity.source} has generated {count + 1} suspicious or attack events "
                f"in the last {window_minutes} minutes."
            ),
            severity="HIGH",
            risk_score=activity.risk_score,
            status=AlertStatus.NEW,
        )
    return None


def update_alert_status(alert_id: int, new_status: str) -> Optional[Alert]:
    """Update an alert's status. Returns updated Alert or None if not found."""
    try:
        status = AlertStatus(new_status.upper())
    except ValueError:
        raise ValueError(f"Invalid status: '{new_status}'. Must be one of: NEW, ACKNOWLEDGED, RESOLVED.")

    alert = Alert.query.get(alert_id)
    if alert is None:
        return None

    alert.status = status
    db.session.commit()
    return alert
