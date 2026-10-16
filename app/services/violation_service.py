"""
Violation Service for SafeSight AI.
Handles CRUD, status transitions, search/filtering, pagination,
statistical aggregations, and CSV export for violations.
"""
import io
import csv
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.db import execute_query, execute_insert

logger = logging.getLogger(__name__)


def create_violation(upload_id: int, detection_id: int, violation_type: str,
                     severity: str, confidence: float, snapshot_path: str,
                     camera_name: str = "Cam 01 - Zone A", location: str = "Zone A",
                     status: str = "detected") -> Optional[int]:
    """Inserts a new violation record and returns its ID."""
    query = """
        INSERT INTO violations (upload_id, detection_id, violation_type, severity, confidence,
                                snapshot_path, camera_name, location, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    return execute_insert(query, (upload_id, detection_id, violation_type, severity,
                                  confidence, snapshot_path, camera_name, location, status))


def get_violations(filters: Optional[Dict[str, Any]] = None,
                   page: int = 1, per_page: int = 15) -> Dict[str, Any]:
    """
    Retrieves a filtered, paginated list of violations.
    Supported filters:
      - violation_type: str or list of str
      - status: str or list of str
      - camera_name: str or list of str
      - severity: str
      - search: str (matches location, camera_name, notes)
      - date_from: YYYY-MM-DD
      - date_to: YYYY-MM-DD
      - sort_by: 'newest', 'oldest', 'severity'
    """
    filters = filters or {}
    where_clauses = ["1=1"]
    params = []

    # Filter by violation type
    v_type = filters.get("violation_type")
    if v_type:
        if isinstance(v_type, list) and len(v_type) > 0:
            placeholders = ",".join(["%s"] * len(v_type))
            where_clauses.append(f"v.violation_type IN ({placeholders})")
            params.extend(v_type)
        elif isinstance(v_type, str) and v_type.lower() != "all":
            where_clauses.append("v.violation_type = %s")
            params.append(v_type)

    # Filter by status
    status = filters.get("status")
    if status:
        if isinstance(status, list) and len(status) > 0:
            placeholders = ",".join(["%s"] * len(status))
            where_clauses.append(f"v.status IN ({placeholders})")
            params.extend(status)
        elif isinstance(status, str) and status.lower() != "all":
            where_clauses.append("v.status = %s")
            params.append(status)

    # Filter by camera
    camera = filters.get("camera_name") or filters.get("camera")
    if camera:
        if isinstance(camera, list) and len(camera) > 0:
            placeholders = ",".join(["%s"] * len(camera))
            where_clauses.append(f"v.camera_name IN ({placeholders})")
            params.extend(camera)
        elif isinstance(camera, str) and camera.lower() != "all":
            where_clauses.append("v.camera_name = %s")
            params.append(camera)

    # Filter by date range
    date_from = filters.get("date_from")
    if date_from:
        where_clauses.append("v.detected_at >= %s")
        params.append(f"{date_from} 00:00:00")

    date_to = filters.get("date_to")
    if date_to:
        where_clauses.append("v.detected_at <= %s")
        params.append(f"{date_to} 23:59:59")

    # Search keyword
    search = filters.get("search")
    if search:
        search_pattern = f"%{search}%"
        where_clauses.append("(v.location LIKE %s OR v.camera_name LIKE %s OR v.notes LIKE %s)")
        params.extend([search_pattern, search_pattern, search_pattern])

    where_str = " AND ".join(where_clauses)

    # Sorting
    sort_by = filters.get("sort_by", "newest")
    if sort_by == "oldest":
        order_str = "ORDER BY v.detected_at ASC"
    elif sort_by == "severity":
        order_str = "ORDER BY CASE v.severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END ASC, v.detected_at DESC"
    else:
        order_str = "ORDER BY v.detected_at DESC"

    # Count total matching
    count_sql = f"SELECT COUNT(*) AS total FROM violations v WHERE {where_str}"
    count_res = execute_query(count_sql, tuple(params), fetch=True)
    total_count = count_res[0]["total"] if count_res else 0

    # Pagination calculation
    offset = max(0, (page - 1) * per_page)
    data_sql = f"""
        SELECT v.id, v.upload_id, v.detection_id, v.violation_type, v.severity,
               v.confidence, v.snapshot_path, v.camera_name, v.location,
               v.status, v.reviewed_by, v.notes, v.detected_at, v.updated_at,
               u.output_path AS annotated_asset
        FROM violations v
        LEFT JOIN uploads u ON v.upload_id = u.id
        WHERE {where_str}
        {order_str}
        LIMIT %s OFFSET %s
    """
    data_params = tuple(params + [per_page, offset])
    rows = execute_query(data_sql, data_params, fetch=True)

    # Format datetime objects into strings for JSON serialization
    formatted_rows = []
    for r in (rows or []):
        item = dict(r)
        if isinstance(item.get("detected_at"), datetime):
            item["detected_at"] = item["detected_at"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(item.get("updated_at"), datetime):
            item["updated_at"] = item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
        formatted_rows.append(item)

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return {
        "items": formatted_rows,
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages
    }


def get_violation_by_id(violation_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single violation."""
    sql = """
        SELECT v.*, u.output_path AS annotated_asset
        FROM violations v
        LEFT JOIN uploads u ON v.upload_id = u.id
        WHERE v.id = %s
    """
    res = execute_query(sql, (violation_id,), fetch=True)
    if not res:
        return None
    item = dict(res[0])
    if isinstance(item.get("detected_at"), datetime):
        item["detected_at"] = item["detected_at"].strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(item.get("updated_at"), datetime):
        item["updated_at"] = item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")
    return item


def update_violation_status(violation_id: int, status: str,
                            reviewed_by: Optional[str] = None,
                            notes: Optional[str] = None) -> bool:
    """Updates the status and review notes for a violation."""
    valid_statuses = {"detected", "pending review", "confirmed", "dismissed", "resolved"}
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

    sql = """
        UPDATE violations
        SET status = %s,
            reviewed_by = COALESCE(%s, reviewed_by),
            notes = COALESCE(%s, notes),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    execute_query(sql, (status, reviewed_by, notes, violation_id), fetch=False, commit=True)
    return True


def get_violation_stats() -> Dict[str, Any]:
    """Returns counts by type, status, and severity."""
    by_type = execute_query(
        "SELECT violation_type, COUNT(*) as cnt FROM violations GROUP BY violation_type"
    ) or []
    by_status = execute_query(
        "SELECT status, COUNT(*) as cnt FROM violations GROUP BY status"
    ) or []
    by_severity = execute_query(
        "SELECT severity, COUNT(*) as cnt FROM violations GROUP BY severity"
    ) or []

    return {
        "by_type": {r["violation_type"]: r["cnt"] for r in by_type},
        "by_status": {r["status"]: r["cnt"] for r in by_status},
        "by_severity": {r["severity"]: r["cnt"] for r in by_severity}
    }


def export_violations_csv(filters: Optional[Dict[str, Any]] = None) -> str:
    """Exports all matching violations as a CSV string."""
    data = get_violations(filters=filters, page=1, per_page=10000)
    items = data["items"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Violation Type", "Severity", "Confidence", "Status",
        "Camera Name", "Location", "Detected At", "Reviewed By", "Notes"
    ])

    for v in items:
        writer.writerow([
            v.get("id"),
            v.get("violation_type"),
            v.get("severity"),
            f"{v.get('confidence', 0.0):.2f}",
            v.get("status"),
            v.get("camera_name"),
            v.get("location"),
            v.get("detected_at"),
            v.get("reviewed_by") or "",
            v.get("notes") or ""
        ])

    return output.getvalue()
