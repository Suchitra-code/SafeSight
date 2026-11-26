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
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 86400  # 24 hours caching for static assets

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
            model_present = os.path.exists(config.MODEL_PATH)
            app.config["DEMO_MODE"] = config.DEMO_MODE or (not model_present)
            if app.config["DEMO_MODE"]:
                logger.warning("SafeSight AI running in DEMO mode (weights not found or DEMO_MODE=true).")
            else:
                logger.info("SafeSight AI configured for PRODUCTION YOLOv8 detection.")
        except Exception as e:
            logger.error(f"Failed to initialize YOLO detector: {e}")
            app.config["DEMO_MODE"] = True

    # Register Route Blueprints
    from app.routes.pages import pages_bp
    from app.routes.api import api_bp
    from app.routes.stream import stream_bp
    from app.routes.auth import auth_bp
    from app.routes.documents import documents_bp
    from app.routes.knowledge import knowledge_bp
    from app.routes.health import health_bp
    from app.routes.assistant import assistant_bp
    from app.routes.investigations import investigations_bp
    from app.routes.copilot import copilot_bp
    from app.routes.command_center import command_center_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(knowledge_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(investigations_bp)
    app.register_blueprint(copilot_bp)
    app.register_blueprint(command_center_bp)

    @app.route("/healthz")
    @app.route("/health")
    def healthz_check():
        return {"status": "ok", "app": "SafeSight AI"}, 200

    @app.before_request
    def require_login():
        """
        Enforce authentication globally:
        If user is not logged in, redirect them to /login.
        Public endpoints (landing page, login, register, health checks, static assets) are excluded.
        """
        from flask import request, redirect, url_for, session

        # Fast-path: root and health checks must always respond 200 without redirect
        if request.path in ("/", "/healthz", "/health"):
            return None

        allowed_endpoints = {
            "pages.landing",
            "auth.login",
            "auth.register",
            "health.get_system_health",
            "healthz_check",
            "static",
        }
        if request.endpoint and request.endpoint not in allowed_endpoints:
            if not session.get("logged_in"):
                return redirect(url_for("auth.login", next=request.url))

    @app.after_request
    def set_performance_headers(response):
        """Adds performance and caching headers for static assets."""
        from flask import request
        if request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=86400, stale-while-revalidate=3600"
        return response

    @app.context_processor
    def inject_global_vars():
        """Injects environment flags into all Jinja2 templates."""
        from flask import session, request
        palette_mode = request.args.get("palette") or session.get("palette_mode") or getattr(config, "PALETTE_MODE", "vivid")
        return {
            "demo_mode": app.config.get("DEMO_MODE", False),
            "palette_mode": palette_mode,
            "app_name": "SafeSight AI",
            "app_subtitle": "AI-Powered Visual Data Analytics and Business Intelligence Platform"
        }

    return app
