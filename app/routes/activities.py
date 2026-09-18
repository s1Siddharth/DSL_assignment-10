"""
OmniShield AI — Activities Routes
GET /api/activities          (paginated, filtered, sorted)
GET /api/activities/<id>     (detail)
"""
import logging
from flask import Blueprint, request
from ..models.activity import Activity
from .utils import success_response, error_response

logger = logging.getLogger(__name__)
activities_bp = Blueprint("activities", __name__)


@activities_bp.route("/activities", methods=["GET"])
def list_activities():
    try:
        # Pagination
        page = max(1, request.args.get("page", 1, type=int))
        per_page = min(100, max(1, request.args.get("per_page", 20, type=int)))

        query = Activity.query

        # Filtering
        prediction = request.args.get("prediction")
        if prediction:
            query = query.filter(Activity.prediction == prediction.lower())

        severity = request.args.get("severity")
        if severity:
            query = query.filter(Activity.severity == severity.upper())

        attack_type = request.args.get("attack_type")
        if attack_type:
            query = query.filter(Activity.attack_type == attack_type.lower())

        date_from = request.args.get("date_from")
        if date_from:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(date_from)
                query = query.filter(Activity.created_at >= dt)
            except ValueError:
                return error_response("VALIDATION_ERROR", "Invalid date_from format. Use ISO 8601.", 400)

        date_to = request.args.get("date_to")
        if date_to:
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(date_to)
                query = query.filter(Activity.created_at <= dt)
            except ValueError:
                return error_response("VALIDATION_ERROR", "Invalid date_to format. Use ISO 8601.", 400)

        # Search in source/destination
        search = request.args.get("search", "").strip()
        if search:
            like = f"%{search}%"
            query = query.filter(
                (Activity.source.like(like)) |
                (Activity.destination.like(like)) |
                (Activity.attack_type.like(like))
            )

        # Sorting
        sort_by = request.args.get("sort_by", "created_at")
        sort_order = request.args.get("sort_order", "desc")
        sort_col = getattr(Activity, sort_by, Activity.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        # Execute
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        return success_response({
            "activities": [a.to_dict() for a in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
            "per_page": per_page,
        })

    except Exception as exc:
        logger.exception("Activities list error")
        return error_response("INTERNAL_ERROR", "Failed to retrieve activities.", 500)


@activities_bp.route("/activities/<int:activity_id>", methods=["GET"])
def get_activity(activity_id: int):
    activity = Activity.query.get(activity_id)
    if activity is None:
        return error_response("NOT_FOUND", f"Activity {activity_id} not found.", 404)
    return success_response(activity.to_dict(include_details=True))
