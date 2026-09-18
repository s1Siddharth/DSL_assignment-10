"""
OmniShield AI — Application Factory
"""
import os
from flask import Flask
from .config import config_by_name
from .extensions import db


def create_app(config_name=None) -> Flask:
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # Load configuration
    app.config.from_object(config_by_name[config_name])

    # Ensure required directories exist
    _ensure_directories(app)

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    _register_blueprints(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


def _ensure_directories(app: Flask) -> None:
    """Create necessary directories if they don't exist."""
    dirs = [
        app.config.get("UPLOAD_FOLDER", "uploads"),
        app.config.get("MODEL_FOLDER", "models/trained"),
        app.config.get("MODEL_METADATA_FOLDER", "models/metadata"),
        "data",
        "instance",
    ]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)


def _register_blueprints(app: Flask) -> None:
    """Register all Flask blueprints."""
    from .routes.dashboard import dashboard_bp
    from .routes.analysis import analysis_bp
    from .routes.activities import activities_bp
    from .routes.alerts import alerts_bp
    from .routes.analytics import analytics_bp
    from .routes.datasets import datasets_bp
    from .routes.models import models_bp
    from .routes.reports import reports_bp
    from .routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp, url_prefix="/api")
    app.register_blueprint(analysis_bp, url_prefix="/api")
    app.register_blueprint(activities_bp, url_prefix="/api")
    app.register_blueprint(alerts_bp, url_prefix="/api")
    app.register_blueprint(analytics_bp, url_prefix="/api")
    app.register_blueprint(datasets_bp, url_prefix="/api")
    app.register_blueprint(models_bp, url_prefix="/api")
    app.register_blueprint(reports_bp, url_prefix="/api")
