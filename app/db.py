"""
Database connection and helper module for SafeSight AI.
Uses connection pooling with mysql.connector, with auto-initialization of schema.
Also provides graceful handling and SQLite fallback if MySQL server is offline.
"""
import os
import sqlite3
import logging
from contextlib import contextmanager
import config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Global pool reference
_pool = None
_use_sqlite_fallback = False
_sqlite_db_path = os.path.join(config.BASE_DIR, "database", "safesight_fallback.db")


def _get_mysql_pool():
    """Initializes or returns the MySQL connection pool."""
    global _pool, _use_sqlite_fallback
    if _use_sqlite_fallback:
        return None

    if _pool is None:
        try:
            import mysql.connector
            from mysql.connector import pooling

            # Attempt to create database first if it doesn't exist
            try:
                temp_conn = mysql.connector.connect(
                    host=config.MYSQL_HOST,
                    port=config.MYSQL_PORT,
                    user=config.MYSQL_USER,
                    password=config.MYSQL_PASSWORD,
                )
                cursor = temp_conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}` CHARACTER SET utf8mb4;")
                temp_conn.commit()
                cursor.close()
                temp_conn.close()
            except Exception:
                raise ConnectionError("MySQL server offline")

            # Create pooled connection
            _pool = pooling.MySQLConnectionPool(
                pool_name="safesight_pool",
                pool_size=5,
                pool_reset_session=True,
                host=config.MYSQL_HOST,
                port=config.MYSQL_PORT,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD,
                database=config.MYSQL_DATABASE,
            )
            logger.info("MySQL connection pool established successfully.")
        except Exception:
            logger.info("MySQL server not detected on localhost:3306. Using built-in SQLite database.")
            _use_sqlite_fallback = True
            _pool = None

    return _pool


def is_using_mysql():
    """Returns True if connected to MySQL, False if using SQLite fallback."""
    global _use_sqlite_fallback, _pool
    return (not _use_sqlite_fallback) and (_pool is not None)


@contextmanager
def get_db_cursor(commit=False, dictionary=True):
    """
    Context manager yielding a database cursor.
    Transparently handles both MySQL and SQLite fallback.
    """
    global _use_sqlite_fallback
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool:
        conn = None
        cursor = None
        try:
            conn = pool.get_connection()
            cursor = conn.cursor(dictionary=dictionary)
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if conn and commit:
                try:
                    conn.rollback()
                except Exception:
                    pass
            logger.error(f"MySQL error: {e}")
            raise e
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    else:
        # SQLite fallback connection
        conn = sqlite3.connect(_sqlite_db_path)
        if dictionary:
            conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if commit:
                conn.rollback()
            logger.error(f"SQLite fallback error: {e}")
            raise e
        finally:
            cursor.close()
            conn.close()


def execute_query(query, params=None, fetch=True, commit=False):
    """
    Executes a SQL query and returns results.
    """
    try:
        with get_db_cursor(commit=commit, dictionary=True) as cursor:
            # Replace MySQL %s with ? for SQLite if in fallback mode
            sql = query
            if _use_sqlite_fallback:
                sql = sql.replace("%s", "?")
            cursor.execute(sql, params or ())
            if fetch:
                rows = cursor.fetchall()
                if _use_sqlite_fallback and rows:
                    return [dict(r) for r in rows]
                return rows
            return None
    except Exception as e:
        logger.error(f"Error in execute_query: {e} | Query: {query}")
        return [] if fetch else None


def execute_insert(query, params=None):
    """
    Executes an INSERT statement and returns the last inserted row id.
    """
    try:
        with get_db_cursor(commit=True, dictionary=True) as cursor:
            sql = query
            if _use_sqlite_fallback:
                sql = sql.replace("%s", "?")
            cursor.execute(sql, params or ())
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error in execute_insert: {e} | Query: {query}")
        return None


def init_db():
    """
    Initializes database tables by executing schema.sql.
    """
    global _use_sqlite_fallback
    schema_path = os.path.join(config.BASE_DIR, "database", "schema.sql")
    if not os.path.exists(schema_path):
        logger.warning(f"Schema file not found at {schema_path}")
        return False

    pool = _get_mysql_pool()
    if not _use_sqlite_fallback and pool:
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            conn = pool.get_connection()
            cursor = conn.cursor()
            # Split commands by semicolon
            for statement in schema_sql.split(";"):
                stmt = statement.strip()
                if stmt and not stmt.upper().startswith("CREATE DATABASE") and not stmt.upper().startswith("USE"):
                    cursor.execute(stmt)
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("MySQL database initialized successfully from schema.sql.")
            return True
        except Exception as e:
            logger.error(f"MySQL schema execution failed ({e}). Switching to SQLite fallback.")
            _use_sqlite_fallback = True

    # Fallback SQLite initialization
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                output_path TEXT,
                camera_name TEXT DEFAULT 'Manual Upload',
                location TEXT DEFAULT 'Zone A - Entrance',
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'processing'
            );
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER,
                frame_no INTEGER DEFAULT 0,
                timestamp_sec REAL DEFAULT 0.0,
                total_people INTEGER DEFAULT 0,
                safe_count INTEGER DEFAULT 0,
                unsafe_count INTEGER DEFAULT 0,
                compliance_percent REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER,
                detection_id INTEGER,
                violation_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                snapshot_path TEXT,
                camera_name TEXT DEFAULT 'Cam 01 - Zone A',
                location TEXT DEFAULT 'Main Facility',
                status TEXT DEFAULT 'detected',
                reviewed_by TEXT,
                notes TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
                FOREIGN KEY (detection_id) REFERENCES detections(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                zone TEXT NOT NULL,
                source TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO cameras (id, name, zone, source, is_active) VALUES
            (1, 'Cam 01 – Zone A', 'Zone A', '0', 1),
            (2, 'Cam 02 – Zone B', 'Zone B', 'sample_zone_b.mp4', 1),
            (3, 'Cam 03 – Exit', 'Exit Gate', 'sample_exit.mp4', 1);
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite fallback database initialized at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite fallback: {e}")
        return False
