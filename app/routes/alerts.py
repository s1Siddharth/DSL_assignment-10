"""
OmniShield AI — Alerts Routes
GET   /api/alerts
PATCH /api/alerts/<id>
"""
import logging
from flask import Blueprint, request
from ..models.alert import Alert, AlertStatus
from ..services.alerts import update_alert_status
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
alerts_bp = Blueprint("alerts", __name__)


@alerts_bp.route("/alerts", methods=["GET"])
def list_alerts():
    try:
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

        query = Alert.query

        status = request.args.get("status")
        if status:
            try:
                status_enum = AlertStatus(status.upper())
                query = query.filter(Alert.status == status_enum)
            except ValueError:
                return error_response("VALIDATION_ERROR", f"Invalid status: {status}", 400)

        severity = request.args.get("severity")
        if severity:
            query = query.filter(Alert.severity == severity.upper())

        query = query.order_by(Alert.created_at.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return success_response({
            "alerts": [a.to_dict() for a in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page,
            "unread_count": Alert.query.filter(Alert.status == AlertStatus.NEW).count(),
        })
    except Exception:
        logger.exception("Alerts list error")
        return error_response("INTERNAL_ERROR", "Failed to retrieve alerts.", 500)


@alerts_bp.route("/alerts/<int:alert_id>", methods=["PATCH"])
def patch_alert(alert_id: int):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if not new_status:
        return error_response("VALIDATION_ERROR", "Field 'status' is required.", 400)
    try:
        alert = update_alert_status(alert_id, new_status)
        if alert is None:
            return error_response("NOT_FOUND", f"Alert {alert_id} not found.", 404)
        return success_response(alert.to_dict(), "Alert status updated.")
    except ValueError as exc:
        return error_response("VALIDATION_ERROR", str(exc), 400)
    except Exception:
        logger.exception("Alert update error")
        return error_response("INTERNAL_ERROR", "Failed to update alert.", 500)
