"""
OmniShield AI — Main Blueprint
Serves the main application SPA at / and /app.
"""
from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@main_bp.route("/app", defaults={"path": ""})
@main_bp.route("/app/<path:path>")
def index(path=""):
    """Single Page Application SPA (Dashboard Shell)."""
    return render_template("index.html")


