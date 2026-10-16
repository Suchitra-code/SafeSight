"""
Flask Application Factory for SafeSight AI.
Initializes configuration, database schemas, blueprint routes,
and YOLOv8 detector singleton.
"""
import os
import logging
from flask import Flask

import config
from app.db import init_db
from app.services.detector import PPEDetector

logger = logging.getLogger(__name__)


def create_app():
    """Constructs and configures the Flask application instance."""
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )

    # Load configuration
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = config.UPLOAD_FOLDER
    app.config["OUTPUT_FOLDER"] = config.OUTPUT_FOLDER
    app.config["REPORT_FOLDER"] = config.REPORT_FOLDER
    app.config["DEMO_MODE"] = config.DEMO_MODE

    # Ensure storage directories exist
    for d in [config.UPLOAD_FOLDER, config.OUTPUT_FOLDER, config.REPORT_FOLDER, config.MODEL_DIR]:
        os.makedirs(d, exist_ok=True)

    # Initialize Database Schema
    with app.app_context():
        try:
            init_db()
        except Exception as e:
            logger.error(f"Failed to auto-initialize database on startup: {e}")

        # Initialize YOLOv8 Detector Singleton
        try:
            detector = PPEDetector()
            app.config["DETECTOR"] = detector
            if detector.is_demo:
                app.config["DEMO_MODE"] = True
                logger.warning("SafeSight AI running in DEMO mode (best.pt weights not found or demo active).")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO detector: {e}")
            app.config["DEMO_MODE"] = True

    # Register Route Blueprints
    from app.routes.pages import pages_bp
    from app.routes.api import api_bp
    from app.routes.stream import stream_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stream_bp)

    @app.context_processor
    def inject_global_vars():
        """Injects environment flags into all Jinja2 templates."""
        return {
            "demo_mode": app.config.get("DEMO_MODE", False),
            "app_name": "SafeSight AI",
            "app_subtitle": "AI-Powered Visual Data Analytics and Business Intelligence Platform"
        }

    return app
