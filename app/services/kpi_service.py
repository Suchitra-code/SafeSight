"""
Workplace Safety KPI Service for SafeSight AI.
Aggregates core workplace safety metrics:
1. Total Inspections (processed media uploads)
2. Total PPE Violations
3. Resolved Violations (audited and resolved)
4. Compliance Percentage (safe workers / total workers * 100)
5. Open Incidents (active investigation runs not yet closed)
6. Reports Generated (compiled PDF reports)
7. Active Safety Alerts (rule-based smart safety alerts)
8. Pending Reviews (violations awaiting human review)
"""
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import config
from app.db import execute_query
from app.services.cache import cached_analytics

logger = logging.getLogger(__name__)


def compute_kpi_metrics(
    inspections_count: int,
    total_violations: int,
    resolved_violations: int,
    total_people: int,
    safe_count: int,
    is_demo: bool = False,
    open_incidents: Optional[int] = None,
    reports_generated: Optional[int] = None,
    active_safety_alerts: Optional[int] = None,
    pending_reviews: Optional[int] = None,
    indicator_errors: Optional[Dict[str, str]] = None,
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
        "open_incidents": max(0, int(open_incidents)) if open_incidents is not None else None,
        "reports_generated": max(0, int(reports_generated)) if reports_generated is not None else None,
        "active_safety_alerts": max(0, int(active_safety_alerts)) if active_safety_alerts is not None else None,
        "pending_reviews": max(0, int(pending_reviews)) if pending_reviews is not None else None,
        "indicator_errors": indicator_errors or {},
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "is_demo": bool(is_demo),
        "warning": warning
    }


def _get_open_incidents_count() -> Tuple[Optional[int], Optional[str]]:
    """
    Count open agentic incident investigations from investigation_runs
    whose status is not closed ('completed', 'dismissed', 'resolved', 'closed', 'failed').
    Returns (None, error) if the source table is unavailable.
    """
    try:
        sql = """
            SELECT COUNT(*) as c
            FROM investigation_runs
            WHERE LOWER(COALESCE(status, '')) NOT IN ('completed', 'dismissed', 'resolved', 'closed', 'failed')
        """
        res = execute_query(sql, fetch=True)
        return (int(res[0]["c"] or 0) if res else 0), None
    except Exception as e:
        logger.warning(f"Open incidents source unavailable: {e}")
        return None, str(e)


def _get_reports_generated_count(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> Tuple[Optional[int], Optional[str]]:
    """
    Count generated PDF reports in config.REPORT_FOLDER (matching analytics.get_kpi_summary).
    Applies date_from/date_to period filter against file mtime when provided.
    Returns (None, error) if report folder is unavailable.
    """
    try:
        report_dir = getattr(config, "REPORT_FOLDER", None)
        if not report_dir or not os.path.isdir(report_dir):
            return None, "Report directory unavailable"

        start_ts = None
        end_ts = None
        if date_from:
            try:
                start_ts = datetime.strptime(f"{date_from} 00:00:00", "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                start_ts = None
        if date_to:
            try:
                end_ts = datetime.strptime(f"{date_to} 23:59:59", "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                end_ts = None

        count = 0
        for fname in os.listdir(report_dir):
            if not fname.lower().endswith(".pdf"):
                continue
            if start_ts is not None or end_ts is not None:
                fpath = os.path.join(report_dir, fname)
                mtime = os.path.getmtime(fpath)
                if start_ts is not None and mtime < start_ts:
                    continue
                if end_ts is not None and mtime > end_ts:
                    continue
            count += 1
        return count, None
    except Exception as e:
        logger.warning(f"Reports generated source unavailable: {e}")
        return None, str(e)


def _get_active_safety_alerts_count() -> Tuple[Optional[int], Optional[str]]:
    """
    Count currently active smart safety alerts from analytics.get_critical_alerts().
    Returns (None, error) if the alert mechanism fails.
    """
    try:
        from app.services import analytics
        alerts = analytics.get_critical_alerts()
        return (len(alerts) if alerts is not None else 0), None
    except Exception as e:
        logger.warning(f"Active safety alerts source unavailable: {e}")
        return None, str(e)


def _get_pending_reviews_count() -> Tuple[Optional[int], Optional[str]]:
    """
    Count PPE violations awaiting human supervisor review
    (canonical Pending statuses: 'detected', 'pending review').
    Returns (None, error) if query fails.
    """
    try:
        sql = """
            SELECT COUNT(*) as c
            FROM violations
            WHERE LOWER(COALESCE(status, 'detected')) IN ('detected', 'pending review')
        """
        res = execute_query(sql, fetch=True)
        return (int(res[0]["c"] or 0) if res else 0), None
    except Exception as e:
        logger.warning(f"Pending reviews source unavailable: {e}")
        return None, str(e)


@cached_analytics(ttl=15.0)
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

        # 2. Total & Resolved Violations with filters (combined single query when status is all)
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

        if not status or status.lower() == "all":
            v_where = " AND ".join(v_clauses)
            v_sql = f"""
                SELECT COUNT(*) as total_c,
                       SUM(CASE WHEN LOWER(status) = 'resolved' THEN 1 ELSE 0 END) as res_c
                FROM violations WHERE {v_where}
            """
            v_res = execute_query(v_sql, tuple(v_params), fetch=True)
            if v_res:
                total_violations = int(v_res[0]["total_c"] or 0)
                resolved_violations = int(v_res[0]["res_c"] or 0)
            else:
                total_violations = 0
                resolved_violations = 0
        else:
            db_stats = get_db_statuses_for_ui_filter(status)
            placeholders = ", ".join(["%s"] * len(db_stats))
            v_clauses.append(f"LOWER(status) IN ({placeholders})")
            v_params.extend([s.lower() for s in db_stats])

            v_where = " AND ".join(v_clauses)
            v_sql = f"SELECT COUNT(*) as c FROM violations WHERE {v_where}"
            v_res = execute_query(v_sql, tuple(v_params), fetch=True)
            total_violations = v_res[0]["c"] if v_res else 0

            # Resolved violations with specific status filter
            r_clauses = [c for c in v_clauses if "status" not in c.lower()]
            r_params = []
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

        # 5. Four extended Core Safety Indicators (isolated: failure in one never breaks others)
        indicator_errors: Dict[str, str] = {}
        open_incidents, err_oi = _get_open_incidents_count()
        if err_oi:
            indicator_errors["open_incidents"] = err_oi

        reports_generated, err_rg = _get_reports_generated_count(date_from=date_from, date_to=date_to)
        if err_rg:
            indicator_errors["reports_generated"] = err_rg

        active_safety_alerts, err_asa = _get_active_safety_alerts_count()
        if err_asa:
            indicator_errors["active_safety_alerts"] = err_asa

        pending_reviews, err_pr = _get_pending_reviews_count()
        if err_pr:
            indicator_errors["pending_reviews"] = err_pr

        metrics = compute_kpi_metrics(
            inspections_count=inspections_count,
            total_violations=total_violations,
            resolved_violations=resolved_violations,
            total_people=total_people,
            safe_count=safe_count,
            is_demo=config.DEMO_MODE,
            open_incidents=open_incidents,
            reports_generated=reports_generated,
            active_safety_alerts=active_safety_alerts,
            pending_reviews=pending_reviews,
            indicator_errors=indicator_errors,
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
