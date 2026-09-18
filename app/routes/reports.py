"""
OmniShield AI — Reports Route
POST /api/report/generate
"""
import logging
from flask import Blueprint, request
from ..services.reports import generate_report
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/report/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    report_type = data.get("type", "summary")
    if report_type not in ("summary", "detailed"):
        return error_response("VALIDATION_ERROR", "Report type must be 'summary' or 'detailed'.", 400)
    try:
        report = generate_report(report_type)
        return success_response(report, f"{report_type.capitalize()} report generated.")
    except Exception:
        logger.exception("Report generation error")
        return error_response("INTERNAL_ERROR", "Failed to generate report.", 500)
