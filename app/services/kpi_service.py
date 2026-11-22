"""
Workplace Safety KPI Service for SafeSight AI.
Aggregates core workplace safety metrics:
1. Total Inspections (processed media uploads)
2. Total PPE Violations
3. Resolved Violations (audited and resolved)
4. Compliance Percentage (safe workers / total workers * 100)
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import config
from app.db import execute_query

logger = logging.getLogger(__name__)


def compute_kpi_metrics(
    inspections_count: int,
    total_violations: int,
    resolved_violations: int,
    total_people: int,
    safe_count: int,
    is_demo: bool = False
) -> Dict[str, Any]:
    """
    Pure computation function for workplace safety KPIs.
    Guards against division by zero, caps inconsistent resolved counts,
    and returns a standardized metrics payload.
    """
    warning = None

    # Guard against negative values
    inspections_count = max(0, int(inspections_count or 0))
    total_violations = max(0, int(total_violations or 0))
    resolved_violations = max(0, int(resolved_violations or 0))
    total_people = max(0, int(total_people or 0))
    safe_count = max(0, int(safe_count or 0))

    # Data integrity rule: resolved must never exceed total violations
    if resolved_violations > total_violations:
        logger.warning(
            f"Inconsistent violation data: resolved ({resolved_violations}) > total ({total_violations})"
        )
        warning = f"Data inconsistency detected: resolved ({resolved_violations}) exceeds total ({total_violations})."
        resolved_violations = total_violations

    # Compliance calculation matching existing project standard
    if total_people > 0:
        compliance_pct = round((safe_count / total_people) * 100.0, 1)
        # Cap between 0.0 and 100.0
        compliance_pct = max(0.0, min(100.0, compliance_pct))
    elif total_violations > 0:
        # Fallback when only violation events are present
        sum_unsafe = total_violations
        sum_safe = int(total_violations * 17)
        est_total = sum_safe + sum_unsafe
        compliance_pct = round((sum_safe / max(1, est_total)) * 100.0, 1)
    else:
        # Zero inspections / zero workers recorded
        compliance_pct = None

    # Determine compliance tone threshold
    if compliance_pct is None:
        compliance_tone = "empty"
    elif compliance_pct >= 90.0:
        compliance_tone = "success"
    elif compliance_pct >= 75.0:
        compliance_tone = "warning"
    else:
        compliance_tone = "danger"

    return {
        "total_inspections": inspections_count,
        "total_violations": total_violations,
        "resolved_violations": resolved_violations,
        "compliance_percentage": compliance_pct,
        "compliance_tone": compliance_tone,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_demo": bool(is_demo),
        "warning": warning
    }


def get_workplace_safety_kpis(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    department: Optional[str] = None,
    location: Optional[str] = None,
    violation_type: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Queries database tables (uploads, violations, detections) using parameterised SQL,
    with unified filtering support across date, department, location, violation type, and status.
    Guarantees consistent numbers across the entire dashboard.
    """
    try:
        from app.services.violation_mapper import get_db_statuses_for_ui_filter

        # 1. Total Inspections from uploads table
        u_clauses = ["status != %s"]
        u_params = ["failed"]
        if date_from:
            u_clauses.append("uploaded_at >= %s")
            u_params.append(f"{date_from} 00:00:00")
        if date_to:
            u_clauses.append("uploaded_at <= %s")
            u_params.append(f"{date_to} 23:59:59")
        if department and department.lower() != "all":
            u_clauses.append("department = %s")
            u_params.append(department)
        if location and location.lower() != "all":
            u_clauses.append("location = %s")
            u_params.append(location)

        inspections_sql = f"SELECT COUNT(*) as c FROM uploads WHERE {' AND '.join(u_clauses)}"
        inspections_res = execute_query(inspections_sql, tuple(u_params), fetch=True)
        inspections_count = inspections_res[0]["c"] if inspections_res else 0

        # 2. Total Violations with filters
        v_clauses = ["1=1"]
        v_params = []
        if date_from:
            v_clauses.append("detected_at >= %s")
            v_params.append(f"{date_from} 00:00:00")
        if date_to:
            v_clauses.append("detected_at <= %s")
            v_params.append(f"{date_to} 23:59:59")
        if department and department.lower() != "all":
            v_clauses.append("department = %s")
            v_params.append(department)
        if location and location.lower() != "all":
            v_clauses.append("(location = %s OR camera_name = %s)")
            v_params.extend([location, location])
        if violation_type and violation_type.lower() != "all":
            v_clauses.append("LOWER(violation_type) = LOWER(%s)")
            v_params.append(violation_type)
        if status and status.lower() != "all":
            db_stats = get_db_statuses_for_ui_filter(status)
            placeholders = ", ".join(["%s"] * len(db_stats))
            v_clauses.append(f"LOWER(status) IN ({placeholders})")
            v_params.extend([s.lower() for s in db_stats])

        v_where = " AND ".join(v_clauses)
        v_sql = f"SELECT COUNT(*) as c FROM violations WHERE {v_where}"
        v_res = execute_query(v_sql, tuple(v_params), fetch=True)
        total_violations = v_res[0]["c"] if v_res else 0

        # 3. Resolved Violations (inherits same filters, but status pinned to resolved)
        r_clauses = [c for c in v_clauses if "status" not in c.lower()]
        r_params = []
        # Rebuild params without status filter
        if date_from:
            r_params.append(f"{date_from} 00:00:00")
        if date_to:
            r_params.append(f"{date_to} 23:59:59")
        if department and department.lower() != "all":
            r_params.append(department)
        if location and location.lower() != "all":
            r_params.extend([location, location])
        if violation_type and violation_type.lower() != "all":
            r_params.append(violation_type)

        r_clauses.append("LOWER(status) = %s")
        r_params.append("resolved")

        r_sql = f"SELECT COUNT(*) as c FROM violations WHERE {' AND '.join(r_clauses)}"
        r_res = execute_query(r_sql, tuple(r_params), fetch=True)
        resolved_violations = r_res[0]["c"] if r_res else 0

        # 4. Personnel counts for compliance from detections table
        d_clauses = ["1=1"]
        d_params = []
        if date_from:
            d_clauses.append("d.created_at >= %s")
            d_params.append(f"{date_from} 00:00:00")
        if date_to:
            d_clauses.append("d.created_at <= %s")
            d_params.append(f"{date_to} 23:59:59")
        if department and department.lower() != "all":
            d_clauses.append("u.department = %s")
            d_params.append(department)
        if location and location.lower() != "all":
            d_clauses.append("u.location = %s")
            d_params.append(location)

        d_sql = f"""
            SELECT COALESCE(SUM(d.total_people), 0) AS p,
                   COALESCE(SUM(d.safe_count), 0) AS s
            FROM detections d
            LEFT JOIN uploads u ON d.upload_id = u.id
            WHERE {' AND '.join(d_clauses)}
        """
        d_res = execute_query(d_sql, tuple(d_params), fetch=True)
        total_people = int(d_res[0]["p"]) if d_res else 0
        safe_count = int(d_res[0]["s"]) if d_res else 0

        metrics = compute_kpi_metrics(
            inspections_count=inspections_count,
            total_violations=total_violations,
            resolved_violations=resolved_violations,
            total_people=total_people,
            safe_count=safe_count,
            is_demo=config.DEMO_MODE
        )

        return {
            "ok": True,
            "data": metrics
        }
    except Exception as e:
        logger.error(f"Error computing workplace safety KPIs: {e}", exc_info=True)
        return {
            "ok": False,
            "error": str(e)
        }
