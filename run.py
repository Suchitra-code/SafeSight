"""
SafeSight AI - PPE Safety Analytics Platform
Main Execution Entrypoint.
Starts the Flask server at http://127.0.0.1:5000 with threaded request handling.
"""
import sys
import logging
from app import create_app
import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("safesight")

app = create_app()

if __name__ == "__main__":
    port = 5000
    host = "127.0.0.1"
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
