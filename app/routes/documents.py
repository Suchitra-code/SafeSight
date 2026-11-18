"""
Document Management REST & Page Routes for SafeSight AI - Milestone 2.
Implements:
- GET /documents (Documents library UI)
- GET /documents/upload (Upload UI)
- GET /documents/<id> (Detail page with tabs)
- GET /repositories (Repositories UI)
- REST APIs:
  - POST /api/documents/upload
  - GET /api/documents
  - GET /api/documents/<id>
  - GET /api/documents/<id>/progress
  - PATCH /api/documents/<id>
  - PATCH /api/documents/<id>/fields/<field_id>
  - PATCH /api/documents/<id>/findings/<finding_id>
  - POST /api/documents/<id>/reprocess
  - DELETE /api/documents/<id>
  - GET /api/documents/<id>/file
  - GET /api/repositories, POST /api/repositories, PATCH, DELETE
  - GET /api/documents/export?format=csv
"""
import os
import io
import csv
import uuid
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, send_file, abort, Response

import config
from app.db import execute_query, execute_insert
from app.services import doc_pipeline, ocr_service

logger = logging.getLogger(__name__)

documents_bp = Blueprint("documents", __name__)


# ---------------------------------------------------------------------------
# HTML Page Views
# ---------------------------------------------------------------------------

@documents_bp.route("/documents")
def documents_page():
    """Documents library overview page."""
    repos = execute_query("SELECT * FROM repositories ORDER BY name ASC") or []
    return render_template(
        "documents.html",
        active_page="documents",
        repositories=[dict(r) for r in repos],
        ocr_available=ocr_service.is_ocr_available()
    )


@documents_bp.route("/documents/upload")
def document_upload_page():
    """Document upload & live progress tracking page."""
    repos = execute_query("SELECT * FROM repositories ORDER BY name ASC") or []
    return render_template(
        "document_upload.html",
        active_page="documents",
        repositories=[dict(r) for r in repos],
        ocr_available=ocr_service.is_ocr_available()
    )


@documents_bp.route("/documents/<int:doc_id>")
def document_detail_page(doc_id):
    """Detailed view for an inspection report or safety manual."""
    doc_rows = execute_query("SELECT * FROM documents WHERE id = %s", (doc_id,), fetch=True)
    if not doc_rows:
        abort(404, description="Document not found")

    doc = dict(doc_rows[0])
    pages = execute_query("SELECT * FROM document_pages WHERE document_id = %s ORDER BY page_no ASC", (doc_id,), fetch=True) or []
    sections = execute_query("SELECT * FROM doc_sections WHERE document_id = %s ORDER BY page_start ASC", (doc_id,), fetch=True) or []
    fields = execute_query("SELECT * FROM report_fields WHERE document_id = %s ORDER BY id ASC", (doc_id,), fetch=True) or []
    findings = execute_query("SELECT * FROM report_findings WHERE document_id = %s ORDER BY severity DESC, id ASC", (doc_id,), fetch=True) or []
    rules = execute_query("SELECT * FROM manual_rules WHERE document_id = %s ORDER BY id ASC", (doc_id,), fetch=True) or []
    procedures = execute_query("SELECT * FROM manual_procedures WHERE document_id = %s ORDER BY id ASC", (doc_id,), fetch=True) or []
    repos = execute_query("SELECT * FROM repositories ORDER BY name ASC") or []

    return render_template(
        "document_detail.html",
        active_page="documents",
        doc=doc,
        pages=[dict(p) for p in pages],
        sections=[dict(s) for s in sections],
        fields=[dict(f) for f in fields],
        findings=[dict(f) for f in findings],
        rules=[dict(r) for r in rules],
        procedures=[dict(pr) for pr in procedures],
        repositories=[dict(r) for r in repos],
        ocr_available=ocr_service.is_ocr_available()
    )


@documents_bp.route("/repositories")
def repositories_page():
    """Repositories management page."""
    return render_template("repositories.html", active_page="repositories")


# ---------------------------------------------------------------------------
# REST API Endpoints
# ---------------------------------------------------------------------------

@documents_bp.route("/api/documents/upload", methods=["POST"])
def api_upload_documents():
    """Uploads one or multiple documents and queues background processing."""
    if "files" not in request.files and "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    files = request.files.getlist("files") or [request.files["file"]]
    if len(files) > 10:
        return jsonify({"error": "Maximum 10 files per upload batch."}), 400

    repo_id_val = request.form.get("repository_id")
    repo_id = int(repo_id_val) if repo_id_val and repo_id_val.isdigit() else None
    forced_doc_type = request.form.get("doc_type", "auto")

    uploaded_records = []

    for f in files:
        if not f.filename:
            continue

        filename = f.filename
        ext = os.path.splitext(filename)[1].lower().replace(".", "")

        if ext not in config.ALLOWED_DOC_EXTENSIONS:
            return jsonify({"error": f"Unsupported format '{ext}'. Allowed: {list(config.ALLOWED_DOC_EXTENSIONS)}"}), 400

        unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"
        save_path = os.path.join(config.DOC_UPLOAD_FOLDER, unique_name)
        f.save(save_path)

        file_size = os.path.getsize(save_path)
        if file_size > config.MAX_CONTENT_LENGTH:
            os.remove(save_path)
            return jsonify({"error": f"File '{filename}' exceeds maximum allowed size (25 MB)."}), 400

        doc_type_initial = forced_doc_type if forced_doc_type in ("inspection_report", "safety_manual", "sop") else "other"
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        doc_id = execute_insert(
            """INSERT INTO documents (repository_id, original_name, stored_name, file_type, file_size, doc_type, title, status, progress_percent)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'uploaded', 0)""",
            (repo_id, filename, save_path, ext, file_size, doc_type_initial, title)
        )

        doc_pipeline.start_processing_pipeline(doc_id)
        uploaded_records.append({
            "id": doc_id,
            "filename": filename,
            "title": title,
            "status": "processing"
        })

    return jsonify({"success": True, "count": len(uploaded_records), "documents": uploaded_records})


@documents_bp.route("/api/documents", methods=["GET"])
def api_list_documents():
    """Lists documents with filtering by repository, doc_type, status, and search query."""
    repo_id = request.args.get("repository_id")
    doc_type = request.args.get("type")
    status = request.args.get("status")
    q = request.args.get("q", "").strip()

    sql = """
        SELECT d.*, r.name as repository_name,
               (SELECT COUNT(*) FROM report_findings WHERE document_id = d.id) as findings_count,
               (SELECT COUNT(*) FROM manual_rules WHERE document_id = d.id) as rules_count
        FROM documents d
        LEFT JOIN repositories r ON d.repository_id = r.id
        WHERE 1=1
    """
    params = []

    if repo_id and repo_id.isdigit():
        sql += " AND d.repository_id = %s"
        params.append(int(repo_id))
    if doc_type and doc_type != "all":
        sql += " AND d.doc_type = %s"
        params.append(doc_type)
    if status and status != "all":
        sql += " AND d.status = %s"
        params.append(status)
    if q:
        sql += " AND (d.title LIKE %s OR d.original_name LIKE %s)"
        params.extend([f"%{q}%", f"%{q}%"])

    sql += " ORDER BY d.uploaded_at DESC"
    rows = execute_query(sql, tuple(params) if params else None, fetch=True) or []
    return jsonify({"documents": [dict(r) for r in rows]})


@documents_bp.route("/api/documents/<int:doc_id>", methods=["GET"])
def api_get_document(doc_id):
    """Returns single document metadata and extracted stats."""
    rows = execute_query("SELECT d.*, r.name as repository_name FROM documents d LEFT JOIN repositories r ON d.repository_id = r.id WHERE d.id = %s", (doc_id,), fetch=True)
    if not rows:
        return jsonify({"error": "Document not found"}), 404
    return jsonify(dict(rows[0]))


@documents_bp.route("/api/documents/<int:doc_id>/progress", methods=["GET"])
def api_document_progress(doc_id):
    """Poll endpoint for pipeline progress."""
    prog = doc_pipeline.get_pipeline_progress(doc_id)
    return jsonify(prog)


@documents_bp.route("/api/documents/<int:doc_id>", methods=["PATCH"])
def api_update_document(doc_id):
    """Updates document metadata (title, doc_type, repository_id, status)."""
    data = request.json or {}
    fields = []
    params = []

    if "title" in data:
        fields.append("title = %s")
        params.append(data["title"].strip())
    if "doc_type" in data:
        fields.append("doc_type = %s")
        params.append(data["doc_type"])
    if "repository_id" in data:
        fields.append("repository_id = %s")
        params.append(data["repository_id"])
    if "status" in data:
        fields.append("status = %s")
        params.append(data["status"])

    if not fields:
        return jsonify({"error": "No fields to update"}), 400

    params.append(doc_id)
    execute_query(f"UPDATE documents SET {', '.join(fields)} WHERE id = %s", tuple(params), fetch=False, commit=True)
    return jsonify({"success": True})


@documents_bp.route("/api/documents/<int:doc_id>/fields/<int:field_id>", methods=["PATCH"])
def api_edit_field(doc_id, field_id):
    """Edits an extracted header field value and marks it as is_edited=True."""
    data = request.json or {}
    new_val = data.get("value")
    execute_query(
        "UPDATE report_fields SET field_value = %s, is_edited = 1 WHERE id = %s AND document_id = %s",
        (new_val, field_id, doc_id), fetch=False, commit=True
    )
    return jsonify({"success": True, "value": new_val, "is_edited": True})


@documents_bp.route("/api/documents/<int:doc_id>/findings/<int:finding_id>", methods=["PATCH"])
def api_edit_finding(doc_id, finding_id):
    """Edits a finding row (status, severity, corrective action)."""
    data = request.json or {}
    fields = []
    params = []
    for k in ["status", "severity", "corrective_action", "responsible_person", "due_date"]:
        if k in data:
            fields.append(f"{k} = %s")
            params.append(data[k])
    if not fields:
        return jsonify({"error": "No update fields provided"}), 400
    params.extend([finding_id, doc_id])
    execute_query(f"UPDATE report_findings SET {', '.join(fields)} WHERE id = %s AND document_id = %s", tuple(params), fetch=False, commit=True)
    return jsonify({"success": True})


@documents_bp.route("/api/documents/<int:doc_id>/reprocess", methods=["POST"])
def api_reprocess_document(doc_id):
    """Triggers background reprocessing for a document."""
    doc_pipeline.start_processing_pipeline(doc_id)
    return jsonify({"success": True, "message": "Reprocessing started"})


@documents_bp.route("/api/documents/<int:doc_id>", methods=["DELETE"])
def api_delete_document(doc_id):
    """Deletes document, chunks, extracted fields and removes file from disk."""
    rows = execute_query("SELECT stored_name FROM documents WHERE id = %s", (doc_id,), fetch=True)
    if rows:
        path = rows[0].get("stored_name")
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    execute_query("DELETE FROM documents WHERE id = %s", (doc_id,), fetch=False, commit=True)
    return jsonify({"success": True, "message": "Document deleted"})


@documents_bp.route("/api/documents/<int:doc_id>/file", methods=["GET"])
def api_download_original(doc_id):
    """Downloads the original uploaded document file."""
    rows = execute_query("SELECT stored_name, original_name FROM documents WHERE id = %s", (doc_id,), fetch=True)
    if not rows or not os.path.exists(rows[0]["stored_name"]):
        abort(404, description="File not found")
    return send_file(rows[0]["stored_name"], download_name=rows[0]["original_name"], as_attachment=True)


# ---------------------------------------------------------------------------
# Repositories APIs
# ---------------------------------------------------------------------------

@documents_bp.route("/api/repositories", methods=["GET"])
def api_get_repositories():
    """Returns repositories with document counts and breakdown."""
    repos = execute_query("""
        SELECT r.*,
               COUNT(d.id) as doc_count,
               MAX(d.uploaded_at) as last_updated
        FROM repositories r
        LEFT JOIN documents d ON r.id = d.repository_id
        GROUP BY r.id
        ORDER BY r.name ASC
    """) or []
    return jsonify({"repositories": [dict(r) for r in repos]})


@documents_bp.route("/api/repositories", methods=["POST"])
def api_create_repository():
    """Creates a new document collection/repository."""
    data = request.json or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    if not name:
        return jsonify({"error": "Repository name is required"}), 400

    new_id = execute_insert(
        "INSERT INTO repositories (name, description) VALUES (%s, %s)",
        (name, desc)
    )
    return jsonify({"success": True, "id": new_id, "name": name})


@documents_bp.route("/api/repositories/<int:repo_id>", methods=["PATCH"])
def api_update_repository(repo_id):
    """Renames or edits repository description."""
    data = request.json or {}
    name = data.get("name", "").strip()
    desc = data.get("description", "").strip()
    execute_query(
        "UPDATE repositories SET name = %s, description = %s WHERE id = %s",
        (name, desc, repo_id), fetch=False, commit=True
    )
    return jsonify({"success": True})


@documents_bp.route("/api/repositories/<int:repo_id>", methods=["DELETE"])
def api_delete_repository(repo_id):
    """Deletes repository and optionally reassigns documents."""
    target_repo_id = request.args.get("move_to")
    if target_repo_id and target_repo_id.isdigit():
        execute_query("UPDATE documents SET repository_id = %s WHERE repository_id = %s", (int(target_repo_id), repo_id), fetch=False, commit=True)
    else:
        execute_query("UPDATE documents SET repository_id = NULL WHERE repository_id = %s", (repo_id,), fetch=False, commit=True)

    execute_query("DELETE FROM repositories WHERE id = %s", (repo_id,), fetch=False, commit=True)
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Findings CSV Export
# ---------------------------------------------------------------------------

@documents_bp.route("/api/documents/export", methods=["GET"])
def api_export_findings():
    """Exports all report findings as a CSV file."""
    findings = execute_query("""
        SELECT f.id, d.title as report_title, f.description, f.category, f.severity,
               f.location, f.corrective_action, f.responsible_person, f.due_date, f.status, f.page_no
        FROM report_findings f
        JOIN documents d ON f.document_id = d.id
        ORDER BY f.id DESC
    """) or []

    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(["Finding ID", "Report Title", "Description", "Category", "Severity", "Location", "Corrective Action", "Responsible Person", "Due Date", "Status", "Page"])

    for f in findings:
        r = dict(f)
        cw.writerow([r["id"], r["report_title"], r["description"], r["category"], r["severity"], r["location"], r["corrective_action"], r["responsible_person"], r["due_date"], r["status"], r["page_no"]])

    output = si.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=safesight_findings_export.csv"}
    )


@documents_bp.route("/api/seed-documents", methods=["POST"])
def api_seed_demo_documents():
    """Loads demo documents for mentor demo."""
    try:
        from database.seed_documents import seed_documents
        count = seed_documents(reset=False)
        return jsonify({"success": True, "message": f"Loaded {count} demo documents successfully."})
    except Exception as e:
        logger.error(f"Failed to seed demo documents: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

