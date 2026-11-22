"""
REST JSON API Routes for SafeSight AI.
Provides endpoints for uploads, async video progress, violation audits,
analytics data for charts/heatmaps, PDF report generation, and demo reset.
"""
import os
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, send_file, current_app, Response, session

import config
from app.db import execute_insert, execute_query
from app.services import processor, violation_service, analytics, report_pdf, kpi_service
from database.seed_demo import seed_demo_data

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/upload", methods=["POST"])
def upload_file():
    """
    Accepts multipart/form-data upload of images or videos.
    Validates file size (max 25MB) and allowed extensions.
    """
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in request"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400

        filename = file.filename
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        is_image = ext in config.ALLOWED_IMAGE_EXTENSIONS
        is_video = ext in config.ALLOWED_VIDEO_EXTENSIONS

        if not (is_image or is_video):
            return jsonify({
                "error": f"Unsupported file extension '{ext}'. Allowed: {list(config.ALLOWED_IMAGE_EXTENSIONS | config.ALLOWED_VIDEO_EXTENSIONS)}"
            }), 400

        # Form metadata
        camera_name = request.form.get("camera_name", "Manual Upload")
        location = request.form.get("location", "Zone A - Entrance")
        conf_threshold = float(request.form.get("confidence", config.CONFIDENCE_THRESHOLD))

        # Save with unique identifier
        unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
        save_path = os.path.join(config.UPLOAD_FOLDER, unique_name)
        file.save(save_path)

        # File size check
        file_size = os.path.getsize(save_path)
        if file_size > config.MAX_CONTENT_LENGTH:
            os.remove(save_path)
            return jsonify({"error": f"File exceeds maximum limit of 25 MB ({file_size / (1024*1024):.1f} MB)"}), 400

        file_type = "image" if is_image else "video"

        # Record upload in DB
        upload_id = execute_insert(
            """
            INSERT INTO uploads (filename, original_name, file_type, file_path, camera_name, location, status)
            VALUES (%s, %s, %s, %s, %s, %s, 'processing')
            """,
            (unique_name, filename, file_type, save_path, camera_name, location)
        )

        if is_image:
            # Process synchronously
            result = processor.process_image(
                save_path, upload_id, confidence=conf_threshold,
                camera_name=camera_name, location=location
            )
            return jsonify({
                "upload_id": upload_id,
                "file_type": "image",
                "status": "done",
                "result": result
            }), 200
        else:
            # Process video asynchronously in background thread
            processor.process_video_async(
                save_path, upload_id, confidence=conf_threshold,
                camera_name=camera_name, location=location,
                frame_skip=config.VIDEO_FRAME_SKIP
            )
            return jsonify({
                "upload_id": upload_id,
                "file_type": "video",
                "status": "processing",
                "message": "Video queued for background processing"
            }), 202

    except Exception as e:
        logger.error(f"Error handling upload: {e}", exc_info=True)
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@api_bp.route("/progress/<int:upload_id>", methods=["GET"])
def get_progress(upload_id):
    """Returns video processing percentage and status message."""
    progress = processor.video_progress_store.get(upload_id, {"percent": 0, "status": "Pending"})
    return jsonify(progress)


@api_bp.route("/results/<int:upload_id>", methods=["GET"])
def get_results(upload_id):
    """Returns complete detection summary and violations for an upload."""
    upload = execute_query("SELECT * FROM uploads WHERE id = %s", (upload_id,), fetch=True)
    if not upload:
        return jsonify({"error": "Upload record not found"}), 404

    upload_data = dict(upload[0])
    detections = execute_query(
        "SELECT * FROM detections WHERE upload_id = %s ORDER BY frame_no ASC", (upload_id,), fetch=True
    )
    violations = execute_query(
        "SELECT * FROM violations WHERE upload_id = %s ORDER BY detected_at DESC", (upload_id,), fetch=True
    )

    # Format datetime strings
    if upload_data.get("uploaded_at"):
        upload_data["uploaded_at"] = str(upload_data["uploaded_at"])

    formatted_v = []
    for v in (violations or []):
        vd = dict(v)
        if vd.get("detected_at"):
            vd["detected_at"] = str(vd["detected_at"])
        formatted_v.append(vd)

    return jsonify({
        "upload": upload_data,
        "detections": [dict(d) for d in (detections or [])],
        "violations": formatted_v
    })


@api_bp.route("/violations", methods=["GET"])
def list_violations():
    """Returns filtered, paginated list of violations with summary counts."""
    try:
        try:
            page = max(1, int(request.args.get("page", 1)))
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Invalid page parameter: must be a positive integer"}), 400

        try:
            raw_size = request.args.get("page_size") or request.args.get("per_page") or 10
            per_page = max(1, min(100, int(raw_size)))
        except (ValueError, TypeError):
            return jsonify({"ok": False, "error": "Invalid page_size parameter: must be an integer between 1 and 100"}), 400

        filters = {
            "type": request.args.getlist("type") or request.args.get("type"),
            "status": request.args.getlist("status") or request.args.get("status"),
            "camera": request.args.get("camera"),
            "severity": request.args.get("severity"),
            "search": request.args.get("q") or request.args.get("search"),
            "date": request.args.get("date"),
            "date_from": request.args.get("from") or request.args.get("date_from"),
            "date_to": request.args.get("to") or request.args.get("date_to"),
            "sort_by": request.args.get("sort_by", "newest")
        }

        # Clean empty filter keys
        filters = {k: v for k, v in filters.items() if v}

        res = violation_service.get_violations(filters=filters, page=page, per_page=per_page)
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error fetching violations: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500


@api_bp.route("/violations/<int:violation_id>", methods=["GET"])
def get_violation(violation_id):
    """Fetches full details for a single violation."""
    v = violation_service.get_violation_by_id(violation_id)
    if not v:
        return jsonify({"ok": False, "error": "Violation not found"}), 404
    return jsonify({"ok": True, "data": v, "violation": v})


@api_bp.route("/violations/<int:violation_id>/history", methods=["GET"])
def get_violation_history_api(violation_id):
    """Fetches audit history for status transitions of a violation."""
    history = violation_service.get_violation_history(violation_id)
    return jsonify({"ok": True, "history": history})


@api_bp.route("/violations/<int:violation_id>/status", methods=["PUT", "PATCH"])
def update_status(violation_id):
    """
    Updates status and review notes for a violation.
    Enforces server-side authentication: requires logged-in user.
    Records audit entry in violation_status_history.
    """
    from flask import session
    if not session.get("logged_in"):
        return jsonify({
            "ok": False,
            "error": "Unauthorized: Authentication required to update violation status"
        }), 401

    try:
        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
        if not new_status or not str(new_status).strip():
            return jsonify({"ok": False, "error": "Missing 'status' parameter"}), 400

        norm_status = str(new_status).strip().lower()
        allowed_statuses = {
            "pending", "reviewed", "resolved",
            "detected", "pending review", "confirmed", "dismissed"
        }
        if norm_status not in allowed_statuses:
            return jsonify({
                "ok": False,
                "error": f"Invalid status: '{new_status}'. Allowed values: {sorted(list(allowed_statuses))}"
            }), 400

        actor = session.get("username") or session.get("user") or data.get("reviewed_by") or "Supervisor"
        notes = data.get("notes")

        res = violation_service.update_violation_status(violation_id, norm_status, reviewed_by=actor, notes=notes)
        return jsonify({
            "ok": True,
            "success": True,
            "data": res.get("violation"),
            "counts": res.get("counts"),
            "message": res.get("message")
        })
    except ValueError as ve:
        # Check if violation was not found
        msg = str(ve)
        status_code = 404 if "not found" in msg.lower() else 400
        return jsonify({"ok": False, "error": msg}), status_code
    except Exception as e:
        logger.error(f"Error updating violation #{violation_id}: {e}", exc_info=True)
        return jsonify({"ok": False, "error": str(e)}), 500



@api_bp.route("/violations/<int:violation_id>/explain", methods=["GET"])
def explain_violation_api(violation_id):
    """Explains a visual violation using linked safety manuals and past inspection reports."""
    try:
        from app.rag.visual_linker import explain_violation
        res = explain_violation(violation_id)
        if not res:
            return jsonify({"error": "Violation not found"}), 404
        if "explanation" not in res:
            res["explanation"] = res.get("narrative") or res.get("what_the_rule_says") or "Violation analyzed against safety manuals."
        return jsonify(res)
    except Exception as e:
        logger.error(f"Error explaining violation {violation_id}: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/violations/<int:violation_id>/snapshot", methods=["GET"])
def get_violation_snapshot(violation_id):
    """Serves the snapshot image for a violation or placeholder if missing."""
    v = violation_service.get_violation_by_id(violation_id)
    if not v or not v.get("snapshot_path"):
        return send_from_directory(os.path.join(config.BASE_DIR, "app", "static", "img"), "placeholder_worker.jpg")
    snap_path = os.path.join(config.OUTPUT_FOLDER, v["snapshot_path"])
    if not os.path.exists(snap_path):
        return send_from_directory(os.path.join(config.BASE_DIR, "app", "static", "img"), "placeholder_worker.jpg")
    return send_file(snap_path)


@api_bp.route("/kpis/workplace-safety", methods=["GET"])
def get_workplace_safety_kpis():
    """
    Returns core workplace safety KPI metrics with unified filter parameters:
    - total_inspections
    - total_violations
    - resolved_violations
    - compliance_percentage
    """
    date_from = request.args.get("from") or request.args.get("date_from")
    date_to = request.args.get("to") or request.args.get("date_to")
    department = request.args.get("department")
    location = request.args.get("location") or request.args.get("camera")
    violation_type = request.args.get("type") or request.args.get("violation_type")
    status = request.args.get("status")

    result = kpi_service.get_workplace_safety_kpis(
        date_from=date_from,
        date_to=date_to,
        department=department,
        location=location,
        violation_type=violation_type,
        status=status
    )
    if not result.get("ok"):
        return jsonify(result), 500
    return jsonify(result), 200


@api_bp.route("/analytics/kpi", methods=["GET"])
def get_kpi():
    """Returns top KPI summary."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    camera = request.args.get("camera")
    return jsonify(analytics.get_kpi_summary(date_from, date_to, camera))


@api_bp.route("/analytics/safety-score", methods=["GET"])
def get_safety_score():
    """Returns circular safety score percentage."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_safety_score(date_from, date_to))


@api_bp.route("/analytics/violations-by-type", methods=["GET"])
def get_violations_by_type():
    """Returns violations grouped by type."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_violations_by_type(date_from, date_to))


@api_bp.route("/analytics/violations-by-severity", methods=["GET"])
def get_violations_by_severity():
    """Returns violations grouped by severity."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_violations_by_severity(date_from, date_to))


@api_bp.route("/analytics/timeseries", methods=["GET"])
def get_timeseries():
    """Returns timeseries for Chart.js."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    camera = request.args.get("camera")
    return jsonify(analytics.get_timeseries(date_from, date_to, camera))


@api_bp.route("/analytics/heatmap", methods=["GET"])
def get_heatmap():
    """Returns 7x24 matrix for Plotly heatmap."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_heatmap_data(date_from, date_to))


@api_bp.route("/analytics/compliance-trend", methods=["GET"])
def get_compliance_trend():
    """Returns daily compliance rate trend."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_compliance_trend(date_from, date_to))


@api_bp.route("/analytics/violations-by-camera", methods=["GET"])
def get_violations_by_camera():
    """Returns violations by camera."""
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    return jsonify(analytics.get_violations_by_camera(date_from, date_to))


@api_bp.route("/analytics/latest-violation", methods=["GET"])
def get_latest_violation():
    """Returns most recent violation."""
    v = analytics.get_latest_violation()
    return jsonify(v or {})


@api_bp.route("/analytics/latest-detections", methods=["GET"])
def get_latest_detections_api():
    """Returns list of recent annotated media detections for carousel preview."""
    limit = int(request.args.get("limit", 6))
    items = analytics.get_latest_detections(limit=limit)
    return jsonify(items)


@api_bp.route("/analytics/ppe-summary", methods=["GET"])
def get_ppe_summary_api():
    """Returns summary counts of compliant vs unsafe personnel and categories."""
    return jsonify(analytics.get_ppe_detection_summary())


@api_bp.route("/analytics/compliance-target-trends", methods=["GET"])
def get_compliance_target_trends_api():
    """Returns achieved compliance trends vs configured target."""
    return jsonify(analytics.get_compliance_target_trends())


@api_bp.route("/analytics/monthly-performance", methods=["GET"])
def get_monthly_performance_api():
    """Returns monthly safety comparison or empty state indicator."""
    return jsonify(analytics.get_monthly_performance())


@api_bp.route("/export/violations-csv", methods=["GET"])
def export_csv():
    """Exports violations as CSV download."""
    csv_content = violation_service.export_violations_csv(request.args.to_dict())
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=safesight_violations_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


@api_bp.route("/reports/generate", methods=["POST"])
def generate_report():
    """Generates PDF report on demand."""
    try:
        data = request.get_json() or {}
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        camera = data.get("camera")
        include_charts = data.get("include_charts", True)

        pdf_path = report_pdf.generate_report(date_from, date_to, camera, include_charts)
        filename = os.path.basename(pdf_path)

        return jsonify({
            "success": True,
            "filename": filename,
            "download_url": f"/api/reports/{filename}/download"
        })
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@api_bp.route("/reports", methods=["GET"])
def list_reports():
    """Lists all generated report files in reports directory."""
    os.makedirs(config.REPORT_FOLDER, exist_ok=True)
    files = []
    for f in os.listdir(config.REPORT_FOLDER):
        if f.endswith(".pdf"):
            full_path = os.path.join(config.REPORT_FOLDER, f)
            mtime = os.path.getmtime(full_path)
            size = os.path.getsize(full_path)
            files.append({
                "filename": f,
                "created_at": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                "size_kb": round(size / 1024, 1),
                "download_url": f"/api/reports/{f}/download"
            })
    files.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify(files)


@api_bp.route("/reports/<path:filename>/download", methods=["GET"])
def download_report(filename):
    """Downloads a generated PDF report."""
    safe_path = os.path.join(config.REPORT_FOLDER, os.path.basename(filename))
    if not os.path.exists(safe_path):
        return jsonify({"error": "Report file not found"}), 404
    return send_file(safe_path, as_attachment=True, download_name=filename)


# =============================================================================
# PREMIUM DASHBOARD ENTERPRISE REST ENDPOINTS (Milestone 5)
# =============================================================================

@api_bp.route("/analytics/filter-options", methods=["GET"])
def get_filter_options_api():
    """Returns distinct department, location, gear type, and status options from real DB."""
    return jsonify(analytics.get_filter_options())


@api_bp.route("/analytics/zone-risk-heatmap", methods=["GET"])
def get_zone_risk_heatmap_api():
    """Returns zone-wise risk heatmap data with real severity weightings."""
    date_from = request.args.get("from") or request.args.get("date_from")
    date_to = request.args.get("to") or request.args.get("date_to")
    department = request.args.get("department")
    return jsonify(analytics.get_zone_risk_heatmap(date_from, date_to, department))


@api_bp.route("/analytics/department-performance", methods=["GET"])
def get_department_performance_api():
    """Returns department-wise performance comparison (grouped bar chart)."""
    date_from = request.args.get("from") or request.args.get("date_from")
    date_to = request.args.get("to") or request.args.get("date_to")
    return jsonify(analytics.get_department_performance(date_from, date_to))


@api_bp.route("/analytics/critical-alerts", methods=["GET"])
def get_critical_alerts_api():
    """Returns real rule-based smart safety alerts."""
    return jsonify(analytics.get_critical_alerts())


@api_bp.route("/analytics/resolution-metrics", methods=["GET"])
def get_resolution_metrics_api():
    """Returns violation resolution metrics and turnaround time."""
    return jsonify(analytics.get_resolution_metrics())


@api_bp.route("/analytics/safety-performance-score", methods=["GET"])
def get_safety_performance_score_api():
    """Returns transparent, formula-grounded Safety Performance Score."""
    return jsonify(analytics.get_safety_performance_score())


@api_bp.route("/analytics/ai-insights", methods=["GET"])
def get_ai_insights_api():
    """Returns deterministic data-driven AI Safety Insights with AI Assistant links."""
    return jsonify(analytics.get_ai_safety_insights())


@api_bp.route("/analytics/forecast", methods=["GET"])
def get_forecast_api():
    """Returns honest predictive safety forecast (7-day moving average)."""
    return jsonify(analytics.get_predictive_safety_forecast())


@api_bp.route("/analytics/export-excel", methods=["GET"])
def export_excel_api():
    """Exports current workplace safety audit data as an Excel-compatible CSV report."""
    import io
    import csv
    from flask import Response

    date_from = request.args.get("from") or request.args.get("date_from")
    date_to = request.args.get("to") or request.args.get("date_to")
    department = request.args.get("department")

    kpis = kpi_service.get_workplace_safety_kpis(date_from=date_from, date_to=date_to, department=department).get("data", {})
    zones = analytics.get_zone_risk_heatmap(date_from=date_from, date_to=date_to, department=department)
    dept_perf = analytics.get_department_performance(date_from=date_from, date_to=date_to)

    output = io.StringIO()
    # Add UTF-8 BOM so Excel opens it with proper encoding
    output.write('\ufeff')
    writer = csv.writer(output)

    # 1. Header
    writer.writerow(["SAFESIGHT AI - WORKPLACE SAFETY AUDIT REPORT"])
    writer.writerow(["Generated At", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(["Design System", "Sunrise Garden Enterprise Theme (0 Black, 0 Blue)"])
    writer.writerow([])

    # 2. Key Metrics Summary
    writer.writerow(["KEY PERFORMANCE INDICATORS"])
    writer.writerow(["Metric", "Value", "Unit", "Notes"])
    writer.writerow(["Total Inspections", kpis.get("total_inspections", 0), "", "Processed media & CCTV audits"])
    writer.writerow(["Total PPE Violations", kpis.get("total_violations", 0), "", "Detected gear infractions"])
    writer.writerow(["Resolved Violations", kpis.get("resolved_violations", 0), "", "Audited and resolved by supervisors"])
    writer.writerow(["Compliance Rate", f"{kpis.get('compliance_percentage', 0)}%", "%", "Standard formula (safe / total people * 100)"])
    writer.writerow([])

    # 3. Department Performance
    writer.writerow(["DEPARTMENT PERFORMANCE COMPARISON"])
    writer.writerow(["Department", "Inspections", "Violations", "Resolved", "Open", "Compliance Rate (%)"])
    for d in dept_perf:
        writer.writerow([d["department"], d["total_inspections"], d["total_violations"], d["resolved_violations"], d["open_violations"], f"{d['compliance_rate']}%"])
    writer.writerow([])

    # 4. Zone Risk Heatmap
    writer.writerow(["ZONE SAFETY RISK HEATMAP"])
    writer.writerow(["Zone / Location", "Department", "Total Violations", "Critical", "High", "Medium", "Low", "Risk Level", "Risk Score"])
    for z in zones:
        writer.writerow([z["zone"], z["department"], z["total_violations"], z["critical_count"], z["high_count"], z["medium_count"], z["low_count"], z["risk_level"], f"{z['risk_score']}%"])

    csv_data = output.getvalue()
    output.close()

    filename = f"SafeSight_Safety_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_bp.route("/inspections/schedules", methods=["GET"])
def get_inspection_schedules_api():
    """Returns list of scheduled safety inspections."""
    return jsonify({"ok": True, "data": analytics.get_upcoming_inspections()})


@api_bp.route("/inspections/schedules", methods=["POST"])
def create_inspection_schedule_api():
    """Creates a new scheduled safety inspection. Server-side auth check."""
    from flask import session
    if not session.get("logged_in"):
        return jsonify({"ok": False, "error": "Unauthorized: Authentication required"}), 401

    data = request.get_json(silent=True) or {}
    title = data.get("title", "").strip()
    department = data.get("department", "").strip()
    location = data.get("location", "").strip()
    scheduled_date = data.get("scheduled_date", "").strip()
    assignee = data.get("assignee", "").strip()
    notes = data.get("notes", "").strip()

    if not title or not department or not location or not scheduled_date or not assignee:
        return jsonify({"ok": False, "error": "Missing required fields: title, department, location, scheduled_date, assignee"}), 400

    sql = """
        INSERT INTO inspection_schedules (title, department, location, scheduled_date, assignee, status, notes)
        VALUES (%s, %s, %s, %s, %s, 'scheduled', %s)
    """
    execute_query(sql, (title, department, location, scheduled_date, assignee, notes), commit=True)
    return jsonify({"ok": True, "message": "Inspection scheduled successfully"}), 201


@api_bp.route("/inspections/schedules/<int:sched_id>/status", methods=["PATCH"])
def update_inspection_schedule_status(sched_id):
    """Updates inspection schedule status (e.g., 'completed'). Server-side auth check."""
    from flask import session
    if not session.get("logged_in"):
        return jsonify({"ok": False, "error": "Unauthorized: Authentication required"}), 401

    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip().lower()
    if new_status not in ["scheduled", "in_progress", "completed", "cancelled"]:
        return jsonify({"ok": False, "error": "Invalid status value"}), 400

    execute_query("UPDATE inspection_schedules SET status = %s WHERE id = %s", (new_status, sched_id), commit=True)
    return jsonify({"ok": True, "message": f"Inspection #{sched_id} status updated to {new_status}"})



@api_bp.route("/seed-demo", methods=["POST"])
def seed_demo():
    """Triggers demo data reload."""
    try:
        seed_demo_data(reset=True)
        return jsonify({"success": True, "message": "Demo data populated (53 violations, 21 days)"})
    except Exception as e:
        logger.error(f"Demo seed failed: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route("/palette/<mode>", methods=["POST", "GET"])
def set_palette(mode):
    """Sets the active palette mode in session ('vivid' or 'mentor_safe')."""
    mode = mode.lower().strip()
    if mode not in ("vivid", "mentor_safe"):
        mode = "vivid"
    session["palette_mode"] = mode
    return jsonify({"success": True, "palette_mode": mode})
