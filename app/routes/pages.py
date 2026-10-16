"""
HTML Page Routes and Asset Serving for SafeSight AI.
Serves Jinja2 templates for Landing, Dashboard, Upload, Result, Live,
Events, and Reports pages, as well as processed snapshots and output media.
"""
import os
from flask import Blueprint, render_template, abort, send_from_directory, current_app

import config
from app.db import execute_query
from app.services import analytics, violation_service

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def landing():
    """Landing / Milestone 01 Overview page."""
    recent_violations = violation_service.get_violations(page=1, per_page=4)["items"]
    kpi = analytics.get_kpi_summary()
    return render_template(
        "landing.html",
        active_page="home",
        accuracy=config.DETECTION_ACCURACY,
        recent_violations=recent_violations,
        kpi=kpi,
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/dashboard")
def dashboard():
    """BI Analytics & Safety Score Dashboard page."""
    kpi = analytics.get_kpi_summary()
    safety_score = analytics.get_safety_score()
    v_by_type = analytics.get_violations_by_type()
    cameras = execute_query("SELECT * FROM cameras WHERE is_active = 1") or []
    latest_v = analytics.get_latest_violation()

    return render_template(
        "dashboard.html",
        active_page="dashboard",
        kpi=kpi,
        safety_score=safety_score,
        v_by_type=v_by_type,
        cameras=[dict(c) for c in cameras],
        latest_violation=latest_v,
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/upload")
def upload():
    """Image & Video Upload page."""
    cameras = execute_query("SELECT * FROM cameras WHERE is_active = 1") or []
    return render_template(
        "upload.html",
        active_page="upload",
        cameras=[dict(c) for c in cameras],
        default_conf=config.CONFIDENCE_THRESHOLD,
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/result/<int:upload_id>")
def result(upload_id):
    """Side-by-side Inspection Result page."""
    upload_res = execute_query("SELECT * FROM uploads WHERE id = %s", (upload_id,), fetch=True)
    if not upload_res:
        abort(404, description="Upload not found")

    upload_data = dict(upload_res[0])
    detections = execute_query(
        "SELECT * FROM detections WHERE upload_id = %s ORDER BY frame_no ASC", (upload_id,), fetch=True
    )
    violations = execute_query(
        "SELECT * FROM violations WHERE upload_id = %s ORDER BY detected_at DESC", (upload_id,), fetch=True
    )

    det_summary = dict(detections[0]) if detections else {
        "total_people": 0, "safe_count": 0, "unsafe_count": 0, "compliance_percent": 0.0
    }

    return render_template(
        "result.html",
        active_page="upload",
        upload=upload_data,
        summary=det_summary,
        violations=[dict(v) for v in (violations or [])],
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/live")
def live():
    """Real-time Multi-camera Live Monitor page."""
    cameras = execute_query("SELECT * FROM cameras WHERE is_active = 1") or []
    recent_violations = violation_service.get_violations(page=1, per_page=6)["items"]
    kpi = analytics.get_kpi_summary()

    return render_template(
        "live.html",
        active_page="live",
        cameras=[dict(c) for c in cameras],
        recent_violations=recent_violations,
        kpi=kpi,
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/events")
def events():
    """Violation Event Audit & Verification page."""
    cameras = execute_query("SELECT * FROM cameras WHERE is_active = 1") or []
    return render_template(
        "events.html",
        active_page="events",
        cameras=[dict(c) for c in cameras],
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/reports")
def reports():
    """Compliance Reports & Audit Logs page."""
    cameras = execute_query("SELECT * FROM cameras WHERE is_active = 1") or []
    return render_template(
        "reports.html",
        active_page="reports",
        cameras=[dict(c) for c in cameras],
        demo_mode=config.DEMO_MODE
    )


@pages_bp.route("/outputs/<path:filename>")
def serve_output(filename):
    """Serves annotated assets, snapshots, and processed media."""
    return send_from_directory(config.OUTPUT_FOLDER, filename)


@pages_bp.route("/uploads/<path:filename>")
def serve_upload(filename):
    """Serves original uploaded media files."""
    return send_from_directory(config.UPLOAD_FOLDER, filename)
