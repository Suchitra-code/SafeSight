"""
SafeSight AI - Standalone Database Initialization CLI
Initializes tables, constraints, default cameras, and schema migrations
for both MySQL and SQLite fallback.

Usage:
    python database/init_db.py
"""
import os
import sys

# Ensure safesight-ai root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.db import init_db, is_using_mysql

if __name__ == "__main__":
    print("=" * 60)
    print("  SafeSight AI – Database Schema Initialization")
    print("=" * 60)

    try:
        success = init_db()
        backend = "MySQL" if is_using_mysql() else "SQLite Fallback"
        if success:
            print(f"[OK] Database initialized successfully using backend: {backend}")
            sys.exit(0)
        else:
            print(f"[FAIL] Database initialization failed on backend: {backend}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Exception during database initialization: {e}", file=sys.stderr)
        sys.exit(1)
