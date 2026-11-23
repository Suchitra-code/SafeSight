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
_sqlite_db_path = os.getenv("SQLITE_DB_PATH", os.path.join(config.BASE_DIR, "database", "safesight_fallback.db"))
try:
    os.makedirs(os.path.dirname(os.path.abspath(_sqlite_db_path)), exist_ok=True)
except Exception:
    pass


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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO cameras (id, name, zone, source, is_active) VALUES
            (1, 'Cam 01 – Zone A', 'Zone A', '0', 1),
            (2, 'Cam 02 – Zone B', 'Zone B', 'sample_zone_b.mp4', 1),
            (3, 'Cam 03 – Exit', 'Exit Gate', 'sample_exit.mp4', 1);

            INSERT OR IGNORE INTO users (id, username, password_hash) VALUES
            (1, 'admin', 'scrypt:32768:8:1$3bYVToFcyEX1lmng$4df3e768428aa7724bec26081556e06d8c360e1a72b3ac0455ab91d5f49149976c6dfbbf0c31ff0255299a2ad6104f38e032c748386655c0f1ec615ce83bddc0'),
            (2, 'suchitragubbala1234@gmail.com', 'scrypt:32768:8:1$3bYVToFcyEX1lmng$4df3e768428aa7724bec26081556e06d8c360e1a72b3ac0455ab91d5f49149976c6dfbbf0c31ff0255299a2ad6104f38e032c748386655c0f1ec615ce83bddc0'),
            (3, 'suchitra', 'scrypt:32768:8:1$3bYVToFcyEX1lmng$4df3e768428aa7724bec26081556e06d8c360e1a72b3ac0455ab91d5f49149976c6dfbbf0c31ff0255299a2ad6104f38e032c748386655c0f1ec615ce83bddc0');

            UPDATE users SET password_hash = 'scrypt:32768:8:1$3bYVToFcyEX1lmng$4df3e768428aa7724bec26081556e06d8c360e1a72b3ac0455ab91d5f49149976c6dfbbf0c31ff0255299a2ad6104f38e032c748386655c0f1ec615ce83bddc0'
            WHERE username IN ('admin', 'suchitra', 'suchitragubbala1234@gmail.com');
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite fallback database initialized at {_sqlite_db_path}")

        # Auto-run Milestone 2 schema migrations
        init_db_milestone2()
        # Auto-run Milestone 3 schema migrations
        init_db_milestone3()
        # Auto-run Milestone 4 schema migrations
        init_db_milestone4()
        # Auto-run Violation Monitoring schema migrations
        init_db_violation_monitoring()
        # Auto-run Premium Dashboard schema migrations
        init_db_premium_dashboard()
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite fallback: {e}")
        return False


def init_db_milestone3():
    """
    Auto-initializes Milestone 3 Multi-modal RAG & Agentic Workflow tables.
    Works for both MySQL and SQLite fallback cleanly using CREATE TABLE IF NOT EXISTS.
    """
    global _use_sqlite_fallback
    m3_schema = os.path.join(config.BASE_DIR, "database", "schema_milestone3.sql")
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool and os.path.exists(m3_schema):
        try:
            with open(m3_schema, "r", encoding="utf-8") as f:
                content = f.read()
            conn = pool.get_connection()
            cur = conn.cursor()
            for stmt in content.split(";"):
                s = stmt.strip()
                if s and not s.upper().startswith("CREATE DATABASE") and not s.upper().startswith("USE"):
                    try:
                        cur.execute(s)
                    except Exception as sqle:
                        logger.warning(f"MySQL M3 statement warning: {sqle}")
            conn.commit()
            cur.close()
            conn.close()
            logger.info("MySQL Milestone 3 tables initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed MySQL M3 init ({e}), using SQLite fallback.")

    # SQLite Fallback M3 DDL
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS visual_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_id INTEGER NOT NULL UNIQUE,
                text TEXT NOT NULL,
                camera TEXT,
                zone TEXT,
                violation_type TEXT,
                severity TEXT,
                event_time TIMESTAMP,
                snapshot_path TEXT,
                source_file TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                mode_used TEXT DEFAULT 'extractive',
                confidence TEXT DEFAULT 'Medium',
                latency_ms REAL DEFAULT 0.0,
                sources_json TEXT,
                feedback INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS investigation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                violation_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                risk_level TEXT DEFAULT 'LOW',
                risk_score INTEGER DEFAULT 1,
                summary TEXT,
                recommendations TEXT,
                approval_status TEXT DEFAULT 'pending',
                supervisor_notes TEXT,
                report_path TEXT,
                current_node TEXT DEFAULT 'load_event',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS agent_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node_name TEXT NOT NULL,
                input_summary TEXT,
                output_summary TEXT,
                status TEXT DEFAULT 'completed',
                duration_ms REAL DEFAULT 0.0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite Milestone 3 tables initialized successfully at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Milestone 3 tables: {e}")
        return False


def init_db_milestone2():
    """
    Auto-initializes Milestone 2 Document Intelligence & Knowledge Base tables.
    Works for both MySQL and SQLite fallback cleanly using CREATE TABLE IF NOT EXISTS.
    """
    global _use_sqlite_fallback
    m2_schema = os.path.join(config.BASE_DIR, "database", "schema_milestone2.sql")
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool and os.path.exists(m2_schema):
        try:
            with open(m2_schema, "r", encoding="utf-8") as f:
                content = f.read()
            conn = pool.get_connection()
            cur = conn.cursor()
            for stmt in content.split(";"):
                s = stmt.strip()
                if s and not s.upper().startswith("CREATE DATABASE") and not s.upper().startswith("USE"):
                    try:
                        cur.execute(s)
                    except Exception as sqle:
                        logger.warning(f"MySQL M2 statement warning: {sqle}")
            conn.commit()
            cur.close()
            conn.close()
            logger.info("MySQL Milestone 2 tables initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed MySQL M2 init ({e}), using SQLite fallback.")

    # SQLite Fallback M2 DDL
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repository_id INTEGER,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                doc_type TEXT DEFAULT 'other',
                title TEXT,
                page_count INTEGER DEFAULT 1,
                status TEXT DEFAULT 'uploaded',
                progress_percent INTEGER DEFAULT 0,
                error_message TEXT,
                avg_confidence REAL DEFAULT 0.0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS document_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_no INTEGER NOT NULL,
                text TEXT,
                used_ocr INTEGER DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS doc_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                title TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                page_start INTEGER DEFAULT 1,
                page_end INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS doc_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                repository_id INTEGER,
                section_id INTEGER DEFAULT NULL,
                page_no INTEGER DEFAULT 1,
                chunk_index INTEGER DEFAULT 0,
                text TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS report_fields (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                field_name TEXT NOT NULL,
                field_value TEXT,
                confidence REAL DEFAULT 1.0,
                page_no INTEGER DEFAULT 1,
                is_edited INTEGER DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS report_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                category TEXT DEFAULT 'other',
                severity TEXT DEFAULT 'LOW',
                location TEXT,
                corrective_action TEXT,
                responsible_person TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'open',
                confidence REAL DEFAULT 1.0,
                page_no INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS manual_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                section_id INTEGER DEFAULT NULL,
                rule_text TEXT NOT NULL,
                ppe_type TEXT DEFAULT 'other',
                page_no INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS manual_procedures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                section_id INTEGER DEFAULT NULL,
                title TEXT NOT NULL,
                steps TEXT,
                page_no INTEGER DEFAULT 1,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS search_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                mode TEXT DEFAULT 'hybrid',
                result_count INTEGER DEFAULT 0,
                took_ms REAL DEFAULT 0.0,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            INSERT OR IGNORE INTO repositories (id, name, description) VALUES
            (1, 'Inspection Reports', 'Official safety audit and site compliance inspection logs'),
            (2, 'Safety Manuals', 'Comprehensive corporate and site PPE safety handbooks'),
            (3, 'SOPs', 'Standard Operating Procedures for equipment and hazardous operations');
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite Milestone 2 tables initialized successfully at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Milestone 2 tables: {e}")
        return False


def init_db_milestone4():
    """
    Auto-initializes Milestone 4 SafeSight Copilot & Mission Control tables.
    Works for both MySQL and SQLite fallback cleanly using CREATE TABLE IF NOT EXISTS.
    """
    global _use_sqlite_fallback
    m4_schema = os.path.join(config.BASE_DIR, "database", "schema_milestone4.sql")
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool and os.path.exists(m4_schema):
        try:
            with open(m4_schema, "r", encoding="utf-8") as f:
                content = f.read()
            conn = pool.get_connection()
            cur = conn.cursor()
            for stmt in content.split(";"):
                s = stmt.strip()
                if s and not s.upper().startswith("CREATE DATABASE") and not s.upper().startswith("USE"):
                    try:
                        cur.execute(s)
                    except Exception as sqle:
                        logger.warning(f"MySQL M4 statement warning: {sqle}")
            conn.commit()
            cur.close()
            conn.close()
            logger.info("MySQL Milestone 4 tables initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed MySQL M4 init ({e}), using SQLite fallback.")

    # SQLite Fallback M4 DDL
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS copilot_runs (
                run_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                question TEXT NOT NULL,
                mode TEXT DEFAULT 'offline',
                intent TEXT,
                route TEXT,
                validation_score INTEGER DEFAULT 0,
                validation_verdict TEXT,
                answer_headline TEXT,
                answer_text TEXT,
                key_facts TEXT,
                actions TEXT,
                total_duration_ms REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS copilot_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                node_name TEXT,
                duration_ms REAL DEFAULT 0.0,
                summary TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS site_zones (
                zone_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                risk_level TEXT DEFAULT 'LOW',
                svg_coords TEXT
            );
        """)
        conn.commit()
        conn.close()
        logger.info(f"SQLite Milestone 4 tables initialized successfully at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Milestone 4 tables: {e}")
        return False


def init_db_violation_monitoring():
    """
    Auto-initializes Violation Monitoring audit history table and safe additive columns.
    Works for both MySQL and SQLite fallback cleanly using CREATE TABLE IF NOT EXISTS.
    """
    global _use_sqlite_fallback
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool:
        try:
            conn = pool.get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS violation_status_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    violation_id INT NOT NULL,
                    old_status VARCHAR(50) NOT NULL,
                    new_status VARCHAR(50) NOT NULL,
                    changed_by VARCHAR(100),
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_vsh_vid (violation_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            # Check and add department column to violations safely
            try:
                cur.execute("SELECT department FROM violations LIMIT 1")
            except Exception:
                try:
                    cur.execute("ALTER TABLE violations ADD COLUMN department VARCHAR(100) DEFAULT NULL")
                except Exception as de:
                    logger.warning(f"Notice on MySQL violations.department migration: {de}")
            conn.commit()
            cur.close()
            conn.close()
            logger.info("MySQL Violation Monitoring tables initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed MySQL Violation Monitoring init ({e}), using SQLite fallback.")

    # SQLite Fallback DDL
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS violation_status_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                violation_id INTEGER NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (violation_id) REFERENCES violations(id) ON DELETE CASCADE
            );
        """)
        # Safe column addition for department
        try:
            cur.execute("ALTER TABLE violations ADD COLUMN department TEXT DEFAULT NULL")
            conn.commit()
        except sqlite3.OperationalError:
            # Column already exists
            pass
        conn.close()
        logger.info(f"SQLite Violation Monitoring tables initialized successfully at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Violation Monitoring tables: {e}")
        return False


def init_db_premium_dashboard():
    """
    Auto-initializes Premium Dashboard schema extensions:
    - inspection_schedules table for P4 scheduling
    - Safe department column on uploads & violations
    - Safe department backfill from real location/zone data
    - Initial upcoming inspection records
    Works for both MySQL and SQLite fallback cleanly using CREATE TABLE IF NOT EXISTS.
    """
    global _use_sqlite_fallback
    pool = _get_mysql_pool()

    if not _use_sqlite_fallback and pool:
        try:
            conn = pool.get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS inspection_schedules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(150) NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    location VARCHAR(150) NOT NULL,
                    scheduled_date DATE NOT NULL,
                    assignee VARCHAR(100) NOT NULL,
                    status VARCHAR(50) DEFAULT 'scheduled',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_is_status (status),
                    INDEX idx_is_date (scheduled_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            try:
                cur.execute("SELECT department FROM uploads LIMIT 1")
            except Exception:
                try:
                    cur.execute("ALTER TABLE uploads ADD COLUMN department VARCHAR(100) DEFAULT NULL")
                except Exception as de:
                    logger.warning(f"Notice on MySQL uploads.department migration: {de}")
            conn.commit()
            cur.close()
            conn.close()
            logger.info("MySQL Premium Dashboard tables initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed MySQL Premium Dashboard init ({e}), using SQLite fallback.")

    # SQLite Fallback DDL
    try:
        conn = sqlite3.connect(_sqlite_db_path)
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS inspection_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                department TEXT NOT NULL,
                location TEXT NOT NULL,
                scheduled_date DATE NOT NULL,
                assignee TEXT NOT NULL,
                status TEXT DEFAULT 'scheduled',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Safe column addition for department on uploads
        try:
            cur.execute("ALTER TABLE uploads ADD COLUMN department TEXT DEFAULT NULL")
            conn.commit()
        except sqlite3.OperationalError:
            pass

        # Backfill department in violations and uploads based on real location data
        cur.execute("UPDATE violations SET department = 'Fabrication' WHERE (location LIKE '%Fabrication%' OR location LIKE '%Zone A%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE violations SET department = 'Assembly' WHERE (location LIKE '%Assembly%' OR location LIKE '%Zone B%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE violations SET department = 'Logistics' WHERE (location LIKE '%Exit%' OR location LIKE '%Zone C%' OR location LIKE '%Warehouse%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE violations SET department = 'Operations' WHERE department IS NULL OR department = ''")

        cur.execute("UPDATE uploads SET department = 'Fabrication' WHERE (location LIKE '%Fabrication%' OR location LIKE '%Zone A%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE uploads SET department = 'Assembly' WHERE (location LIKE '%Assembly%' OR location LIKE '%Zone B%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE uploads SET department = 'Logistics' WHERE (location LIKE '%Exit%' OR location LIKE '%Zone C%') AND (department IS NULL OR department = '')")
        cur.execute("UPDATE uploads SET department = 'Operations' WHERE department IS NULL OR department = ''")
        conn.commit()

        # Seed initial upcoming inspections if table is empty
        cur.execute("SELECT COUNT(*) FROM inspection_schedules")
        count = cur.fetchone()[0]
        if count == 0:
            cur.executemany("""
                INSERT INTO inspection_schedules (title, department, location, scheduled_date, assignee, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [
                ('PPE Compliance Routine Audit', 'Fabrication', 'Zone A - Fabrication', '2026-11-24', 'Sarah Jenkins (Safety Lead)', 'scheduled', 'Quarterly heavy welding and helmet checks'),
                ('High-Hazard Zone Assessment', 'Assembly', 'Zone B - Assembly Line', '2026-11-25', 'Marcus Chen (Senior Inspector)', 'scheduled', 'Conveyor belt guard & safety vest inspection'),
                ('Exit Clearance & Signage Audit', 'Logistics', 'Zone C - Exit Gate', '2026-11-26', 'Elena Rostova (Compliance Specialist)', 'scheduled', 'Emergency egress & night shift visibility check'),
            ])
            conn.commit()

        conn.close()
        logger.info(f"SQLite Premium Dashboard tables initialized successfully at {_sqlite_db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite Premium Dashboard tables: {e}")
        return False


