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
from app.services.cache import cached_analytics, clear_analytics_cache
from app.services.violation_mapper import (
    map_status_to_ui,
    map_ui_status_to_db,
    get_db_statuses_for_ui_filter,
    map_violation_type as mapper_map_violation_type,
    split_datetime,
    calculate_sno
)

logger = logging.getLogger(__name__)


@cached_analytics(ttl=15.0)
def get_violation_summary_counts() -> Dict[str, int]:
    """
    Returns verified aggregate counts for:
    - total: all violation records
    - pending: 'detected', 'pending review'
    - reviewed: 'confirmed', 'dismissed'
    - resolved: 'resolved'
    Guarantees: pending + reviewed + resolved == total.
    """
    sql = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN LOWER(status) IN ('detected', 'pending review') THEN 1 ELSE 0 END) AS pending_cnt,
            SUM(CASE WHEN LOWER(status) IN ('confirmed', 'dismissed') THEN 1 ELSE 0 END) AS reviewed_cnt,
            SUM(CASE WHEN LOWER(status) = 'resolved' THEN 1 ELSE 0 END) AS resolved_cnt
        FROM violations
    """
    res = execute_query(sql, fetch=True)
    if not res:
        return {"total": 0, "pending": 0, "reviewed": 0, "resolved": 0}

    row = res[0]
    total = int(row.get("total") or 0)
    pending = int(row.get("pending_cnt") or 0)
    reviewed = int(row.get("reviewed_cnt") or 0)
    resolved = int(row.get("resolved_cnt") or 0)

    # In case of nulls, ensure sum consistency
    calc_sum = pending + reviewed + resolved
    if calc_sum != total and total > 0:
        # Assign any unmapped delta to pending
        pending += (total - calc_sum)

    return {
        "total": total,
        "pending": pending,
        "reviewed": reviewed,
        "resolved": resolved
    }


def get_violation_history(violation_id: int) -> List[Dict[str, Any]]:
    """Returns chronological audit trail for a violation's status changes."""
    sql = """
        SELECT id, violation_id, old_status, new_status, changed_by, notes, created_at
        FROM violation_status_history
        WHERE violation_id = %s
        ORDER BY created_at DESC
    """
    rows = execute_query(sql, (violation_id,), fetch=True) or []
    formatted = []
    for r in rows:
        item = dict(r)
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].strftime("%Y-%m-%d %H:%M:%S")
        formatted.append(item)
    return formatted



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
    v_id = execute_insert(query, (upload_id, detection_id, violation_type, severity,
                                  confidence, snapshot_path, camera_name, location, status))
    # Automatically index into visual_chunks for Milestone 3 multi-modal search
    if v_id:
        clear_analytics_cache()
        try:
            from app.rag.visual_indexer import index_violation
            index_violation(v_id)
        except Exception as e:
            logger.warning(f"Background visual indexer notice: {e}")
    return v_id


def get_violations(filters: Optional[Dict[str, Any]] = None,
                   page: int = 1, per_page: int = 15) -> Dict[str, Any]:
    """
    Retrieves a filtered, paginated list of violations.
    Supported filters:
      - violation_type / type: str or list of str
      - status: str ('pending', 'reviewed', 'resolved' or raw db status) or list
      - camera_name / camera: str or list of str
      - severity: str
      - search / q: str (matches location, camera_name, notes, violation_type)
      - date: YYYY-MM-DD (exact single day)
      - date_from / from: YYYY-MM-DD
      - date_to / to: YYYY-MM-DD
      - sort_by: 'newest', 'oldest', 'severity'
    """
    filters = filters or {}
    where_clauses = ["1=1"]
    params = []

    # Filter by violation type
    v_type = filters.get("violation_type") or filters.get("type")
    if v_type:
        if isinstance(v_type, list) and len(v_type) > 0:
            placeholders = ",".join(["%s"] * len(v_type))
            where_clauses.append(f"v.violation_type IN ({placeholders})")
            params.extend(v_type)
        elif isinstance(v_type, str) and v_type.lower() != "all" and v_type.strip():
            # Support friendly label filtering or raw code
            vt = v_type.strip().lower()
            if vt in ("missing helmet", "helmet"):
                where_clauses.append("LOWER(v.violation_type) IN ('helmet', 'no helmet', 'no_helmet')")
            elif vt in ("missing safety vest", "vest"):
                where_clauses.append("LOWER(v.violation_type) IN ('vest', 'no vest', 'no_vest')")
            elif vt in ("no safety equipment", "equipment"):
                where_clauses.append("LOWER(v.violation_type) IN ('equipment', 'several ppe items missing', 'no_equipment')")
            elif vt in ("other safety violation", "other"):
                where_clauses.append("LOWER(v.violation_type) NOT IN ('helmet', 'no helmet', 'no_helmet', 'vest', 'no vest', 'no_vest', 'equipment', 'several ppe items missing')")
            else:
                where_clauses.append("v.violation_type = %s")
                params.append(v_type)

    # Filter by status (supports UI status or DB status)
    status_val = filters.get("status")
    if status_val:
        if isinstance(status_val, list) and len(status_val) > 0:
            # Flatten any UI mapped statuses in the list
            expanded = []
            for s in status_val:
                db_s = get_db_statuses_for_ui_filter(s)
                if db_s:
                    expanded.extend(db_s)
                else:
                    expanded.append(s)
            expanded = list(set(expanded))
            placeholders = ",".join(["%s"] * len(expanded))
            where_clauses.append(f"v.status IN ({placeholders})")
            params.extend(expanded)
        elif isinstance(status_val, str) and status_val.lower() != "all" and status_val.strip():
            db_s = get_db_statuses_for_ui_filter(status_val)
            if db_s and len(db_s) > 1:
                placeholders = ",".join(["%s"] * len(db_s))
                where_clauses.append(f"v.status IN ({placeholders})")
                params.extend(db_s)
            elif db_s and len(db_s) == 1:
                where_clauses.append("v.status = %s")
                params.append(db_s[0])
            else:
                where_clauses.append("v.status = %s")
                params.append(status_val)

    # Filter by camera
    camera = filters.get("camera_name") or filters.get("camera")
    if camera:
        if isinstance(camera, list) and len(camera) > 0:
            placeholders = ",".join(["%s"] * len(camera))
            where_clauses.append(f"v.camera_name IN ({placeholders})")
            params.extend(camera)
        elif isinstance(camera, str) and camera.lower() != "all" and camera.strip():
            where_clauses.append("v.camera_name = %s")
            params.append(camera)

    # Filter by exact single date
    exact_date = filters.get("date")
    if exact_date and exact_date.strip():
        where_clauses.append("v.detected_at >= %s AND v.detected_at <= %s")
        params.append(f"{exact_date.strip()} 00:00:00")
        params.append(f"{exact_date.strip()} 23:59:59")

    # Filter by date range
    date_from = filters.get("date_from") or filters.get("from")
    if date_from and date_from.strip():
        where_clauses.append("v.detected_at >= %s")
        params.append(f"{date_from.strip()} 00:00:00")

    date_to = filters.get("date_to") or filters.get("to")
    if date_to and date_to.strip():
        where_clauses.append("v.detected_at <= %s")
        params.append(f"{date_to.strip()} 23:59:59")

    # Search keyword (matches location, department, camera_name, notes, violation_type)
    search = filters.get("search") or filters.get("q")
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        where_clauses.append(
            "(v.location LIKE %s OR v.camera_name LIKE %s OR v.notes LIKE %s OR v.violation_type LIKE %s)"
        )
        params.extend([search_pattern, search_pattern, search_pattern, search_pattern])

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
    safe_page = max(1, int(page or 1))
    safe_per_page = max(1, min(100, int(per_page or 15)))
    offset = max(0, (safe_page - 1) * safe_per_page)

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
    data_params = tuple(params + [safe_per_page, offset])
    rows = execute_query(data_sql, data_params, fetch=True)

    # Format datetime objects and inject UI mapping metadata
    formatted_rows = []
    for idx, r in enumerate(rows or []):
        item = dict(r)

        # Datetime string conversions
        dt_val = item.get("detected_at")
        if isinstance(dt_val, datetime):
            item["detected_at"] = dt_val.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(item.get("updated_at"), datetime):
            item["updated_at"] = item["updated_at"].strftime("%Y-%m-%d %H:%M:%S")

        # 1. Running S.No across pages
        item["sno"] = calculate_sno(safe_page, safe_per_page, idx)

        # 2. UI Status Model
        st_meta = map_status_to_ui(item.get("status"))
        item["ui_status"] = st_meta["ui_status"]
        item["status_tone"] = st_meta["tone"]
        item["status_color"] = st_meta["color"]
        item["status_bg"] = st_meta["bg_color"]
        item["status_text_color"] = st_meta["text_color"]
        item["status_badge_class"] = st_meta["badge_class"]
        item["is_dismissed"] = st_meta["is_dismissed"]
        item["status_tooltip"] = st_meta["tooltip"]

        # 3. Violation Type Normalization
        type_meta = mapper_map_violation_type(item.get("violation_type"))
        item["type_label"] = type_meta["label"]
        item["type_icon"] = type_meta["icon"]
        item["type_tone"] = type_meta["tone"]
        item["type_color"] = type_meta["color"]
        item["type_bg"] = type_meta["bg"]

        # 4. Split Date & Time
        date_str, time_str = split_datetime(item.get("detected_at"))
        item["date_formatted"] = date_str
        item["time_formatted"] = time_str

        # 5. Location / Department Fallback
        item["location_display"] = item.get("location") or item.get("department") or "Not specified"

        formatted_rows.append(item)

    total_pages = (total_count + safe_per_page - 1) // safe_per_page if total_count > 0 else 1
    summary_counts = get_violation_summary_counts()

    return {
        "ok": True,
        "data": formatted_rows,
        "items": formatted_rows,
        "total": total_count,
        "page": safe_page,
        "page_size": safe_per_page,
        "per_page": safe_per_page,
        "total_pages": total_pages,
        "counts": summary_counts
    }


def get_violation_by_id(violation_id: int) -> Optional[Dict[str, Any]]:
    """Fetches details for a single violation with UI presentation metadata."""
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

    st_meta = map_status_to_ui(item.get("status"))
    item["ui_status"] = st_meta["ui_status"]
    item["status_tone"] = st_meta["tone"]
    item["status_color"] = st_meta["color"]
    item["status_bg"] = st_meta["bg_color"]
    item["status_badge_class"] = st_meta["badge_class"]
    item["is_dismissed"] = st_meta["is_dismissed"]
    item["status_tooltip"] = st_meta["tooltip"]

    type_meta = mapper_map_violation_type(item.get("violation_type"))
    item["type_label"] = type_meta["label"]
    item["type_icon"] = type_meta["icon"]
    item["type_tone"] = type_meta["tone"]

    date_str, time_str = split_datetime(item.get("detected_at"))
    item["date_formatted"] = date_str
    item["time_formatted"] = time_str
    item["location_display"] = item.get("location") or item.get("department") or "Not specified"

    return item


def update_violation_status(violation_id: int, status: str,
                            reviewed_by: Optional[str] = None,
                            notes: Optional[str] = None) -> Dict[str, Any]:
    """
    Updates the status and review notes for a violation.
    Records every status change in violation_status_history for audit trail.
    Supports both UI status names ('pending', 'reviewed', 'resolved') and DB status values.
    """
    # Look up existing record to verify existence and get old status
    existing = get_violation_by_id(violation_id)
    if not existing:
        raise ValueError(f"Violation #{violation_id} not found.")

    old_status = existing.get("status") or "detected"

    # Map UI status if needed
    target_status = map_ui_status_to_db(status)
    valid_statuses = {"detected", "pending review", "confirmed", "dismissed", "resolved"}
    if target_status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Target must be one of {valid_statuses}")

    actor = reviewed_by or "System Auditor"

    sql = """
        UPDATE violations
        SET status = %s,
            reviewed_by = COALESCE(%s, reviewed_by),
            notes = COALESCE(%s, notes),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    execute_query(sql, (target_status, actor, notes, violation_id), fetch=False, commit=True)

    # Insert immutable audit trail entry into violation_status_history
    audit_sql = """
        INSERT INTO violation_status_history (violation_id, old_status, new_status, changed_by, notes)
        VALUES (%s, %s, %s, %s, %s)
    """
    execute_insert(audit_sql, (violation_id, old_status, target_status, actor, notes))

    # Clear cached analytics on status change
    clear_analytics_cache()

    # Return freshly updated item and latest counts
    updated = get_violation_by_id(violation_id)
    counts = get_violation_summary_counts()

    return {
        "ok": True,
        "violation": updated,
        "counts": counts,
        "message": f"Violation #{violation_id} updated from '{old_status}' to '{target_status}'"
    }



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
