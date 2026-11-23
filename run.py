"""
SafeSight AI - PPE Safety Analytics Platform
Main Execution Entrypoint.
Starts the Flask server with threaded request handling.
In production (Render), Gunicorn calls `run:app` directly and manages
host/port binding via its own -b flag. The __main__ block is only used
for local development (`python run.py`).
"""
import os
import sys
import logging
from app import create_app
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("safesight")

# Module-level app object — Gunicorn and Vercel import this as `run:app`
app = create_app()
application = app

if __name__ == "__main__":
    # In container and cloud environments, host must bind to 0.0.0.0 so reverse proxies can reach it.
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "0.0.0.0")
    print("\n" + "=" * 65)
    print("  SAFESIGHT AI – PPE Safety Analytics Platform")
    print("  AI-Powered Visual Data Analytics & Business Intelligence")
    from app.db import is_using_mysql
    db_status = f"MySQL ({config.MYSQL_DATABASE})" if is_using_mysql() else "Built-in SQLite (safesight_fallback.db)"
    print(f"  * Status: Server running at http://{host}:{port}/")
    print(f"  * Mode: {'DEMO MODE (Simulation active)' if app.config.get('DEMO_MODE') else 'PRODUCTION (YOLOv8 active)'}")
    print(f"  * Database: {db_status}")
    print("=" * 65 + "\n")

    app.run(
        host=host,
        port=port,
        debug=config.FLASK_DEBUG,
        threaded=True
    )
