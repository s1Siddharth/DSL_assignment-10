"""
OmniShield AI — Dashboard Route
GET /api/dashboard
"""
import logging
from flask import Blueprint
from ..services.dashboard import get_dashboard_data
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
def dashboard():
    try:
        data = get_dashboard_data()
        return success_response(data)
    except Exception as exc:
        logger.exception("Dashboard error")
        return error_response("INTERNAL_ERROR", "Failed to load dashboard data.", 500)
