"""
Investigation API Routes for SafeSight AI - Milestone 3.
Provides endpoints for starting, monitoring, approving, and reviewing
agentic investigations for safety violations.
"""
import os
import logging
from flask import Blueprint, request, jsonify, send_from_directory, abort

import config
from app.agents import runner

investigations_bp = Blueprint("investigations", __name__, url_prefix="/api/investigations")
logger = logging.getLogger(__name__)


@investigations_bp.route("/", methods=["GET"])
def list_runs():
    """List paginated investigation runs."""
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        data = runner.list_investigations(page=page, per_page=per_page)
        return jsonify(data)
    except Exception as e:
        logger.exception("Error listing investigations")
        return jsonify({"error": str(e)}), 500


@investigations_bp.route("/start/<int:violation_id>", methods=["POST"])
def start_run(violation_id):
    """Starts or retrieves an active investigation for a violation."""
    try:
        result = runner.start_investigation_run(violation_id)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error starting investigation for violation {violation_id}")
        return jsonify({"error": str(e)}), 500


@investigations_bp.route("/<run_id>", methods=["GET"])
def get_run(run_id):
    """Retrieves full status and execution steps for a specific run."""
    try:
        data = runner.get_run_status(run_id)
        if not data:
            return jsonify({"error": f"Investigation run '{run_id}' not found"}), 404
        return jsonify(data)
    except Exception as e:
        logger.exception(f"Error retrieving investigation {run_id}")
        return jsonify({"error": str(e)}), 500


@investigations_bp.route("/<run_id>/approve", methods=["POST"])
def approve_run(run_id):
    """Supervisor approves corrective actions of an investigation."""
    try:
        req_data = request.get_json(silent=True) or {}
        notes = req_data.get("notes", "Approved by safety supervisor.")
        result = runner.resume_investigation_run(run_id, decision="approved", notes=notes)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error approving investigation {run_id}")
        return jsonify({"error": str(e)}), 500


@investigations_bp.route("/<run_id>/reject", methods=["POST"])
def reject_run(run_id):
    """Supervisor rejects/dismisses an investigation."""
    try:
        req_data = request.get_json(silent=True) or {}
        notes = req_data.get("notes", "Dismissed by safety supervisor.")
        result = runner.resume_investigation_run(run_id, decision="rejected", notes=notes)
        return jsonify(result)
    except Exception as e:
        logger.exception(f"Error rejecting investigation {run_id}")
        return jsonify({"error": str(e)}), 500


@investigations_bp.route("/<run_id>/pdf", methods=["GET"])
def download_pdf(run_id):
    """Downloads the generated investigation PDF report."""
    try:
        data = runner.get_run_status(run_id)
        if not data or not data.get("report_path"):
            return jsonify({"error": "Report PDF not generated yet"}), 404
        filename = data["report_path"]
        return send_from_directory(config.REPORT_FOLDER, filename, as_attachment=True)
    except Exception as e:
        logger.exception(f"Error downloading PDF for {run_id}")
        return jsonify({"error": str(e)}), 500
