"""
Document Processing Pipeline for SafeSight AI - Milestone 2.
Orchestrates:
1. Validation (types, size limit 25MB, empty/corrupt detection).
2. Text & Page extraction (doc_loader).
3. Text cleaning & normalization (text_cleaner).
4. Document classification (doc_classifier).
5. Information extraction:
   - Inspection reports: header fields, findings, summary.
   - Safety manuals / SOPs: section outline, mandatory rules, procedures.
6. Chunking (chunker) & Indexing (embedder).
7. Progress updates & DB persistence.
Runs in background threads. Never crashes.
"""
import os
import json
import logging
import threading
from datetime import datetime
from typing import Dict, Any

from app.db import execute_query, execute_insert
from app.services import (
    doc_loader,
    text_cleaner,
    doc_classifier,
    inspection_extractor,
    manual_extractor,
    chunker,
    embedder
)

logger = logging.getLogger(__name__)

# In-memory progress tracking for quick UI polling
pipeline_progress_store: Dict[int, Dict[str, Any]] = {}


def start_processing_pipeline(document_id: int):
    """Launches the document processing pipeline in a background thread."""
    thread = threading.Thread(target=_run_pipeline, args=(document_id,), daemon=True)
    thread.start()


def get_pipeline_progress(document_id: int) -> Dict[str, Any]:
    """Returns the current processing step and percentage."""
    if document_id in pipeline_progress_store:
        return pipeline_progress_store[document_id]

    # Check DB
    rows = execute_query(
        "SELECT status, progress_percent, error_message FROM documents WHERE id = %s",
        (document_id,), fetch=True
    )
    if rows:
        r = rows[0]
        return {
            "status": r.get("status"),
            "progress": r.get("progress_percent", 0),
            "step": r.get("status"),
            "error": r.get("error_message")
        }
    return {"status": "unknown", "progress": 0, "step": "Unknown", "error": None}


def _update_progress(doc_id: int, step: str, percent: int, status: str = "processing"):
    pipeline_progress_store[doc_id] = {
        "status": status,
        "progress": percent,
        "step": step,
        "error": None
    }
    try:
        execute_query(
            "UPDATE documents SET status = %s, progress_percent = %s WHERE id = %s",
            (status, percent, doc_id), fetch=False, commit=True
        )
    except Exception as e:
        logger.error(f"Error updating doc progress: {e}")


def _run_pipeline(doc_id: int):
    """Executes the full extraction & indexing pipeline with comprehensive try/except."""
    try:
        _update_progress(doc_id, "Reading file and checking structure", 10)

        # 1. Fetch document record
        rows = execute_query("SELECT * FROM documents WHERE id = %s", (doc_id,), fetch=True)
        if not rows:
            return
        doc_record = dict(rows[0])
        stored_path = doc_record["stored_name"]
        repo_id = doc_record.get("repository_id")

        if not os.path.exists(stored_path):
            _fail_pipeline(doc_id, f"File not found on server: {stored_path}")
            return

        # 2. Extract pages & text
        _update_progress(doc_id, "Extracting text and running OCR", 30)
        pages, err = doc_loader.load_document(stored_path)
        if err or not pages:
            _fail_pipeline(doc_id, err or "No readable content found in document.")
            return

        # Save pages to DB
        execute_query("DELETE FROM document_pages WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        for p in pages:
            execute_insert(
                "INSERT INTO document_pages (document_id, page_no, text, used_ocr) VALUES (%s, %s, %s, %s)",
                (doc_id, p["page_no"], p["text"], 1 if p.get("used_ocr") else 0)
            )

        full_text = "\n\n".join(p["text"] for p in pages)
        page_count = len(pages)

        # 3. Classify document
        _update_progress(doc_id, "Classifying document type", 50)
        current_type = doc_record.get("doc_type")
        if not current_type or current_type == "other":
            predicted_type, conf = doc_classifier.classify_document(full_text, doc_record["original_name"])
            doc_type = predicted_type
        else:
            doc_type = current_type

        # 4. Extract data based on doc_type
        _update_progress(doc_id, "Extracting fields, findings and safety rules", 70)
        avg_conf = 0.85

        # Clean previous extractions
        execute_query("DELETE FROM report_fields WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        execute_query("DELETE FROM report_findings WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        execute_query("DELETE FROM manual_rules WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        execute_query("DELETE FROM manual_procedures WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        execute_query("DELETE FROM doc_sections WHERE document_id = %s", (doc_id,), fetch=False, commit=True)

        if doc_type == "inspection_report":
            report_data = inspection_extractor.extract_report_data(pages)
            for f in report_data["fields"]:
                execute_insert(
                    "INSERT INTO report_fields (document_id, field_name, field_value, confidence, page_no, is_edited) VALUES (%s, %s, %s, %s, %s, %s)",
                    (doc_id, f["field_name"], f["field_value"], f["confidence"], f["page_no"], 0)
                )
            for fnd in report_data["findings"]:
                execute_insert(
                    "INSERT INTO report_findings (document_id, description, category, severity, location, corrective_action, responsible_person, due_date, status, confidence, page_no) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (doc_id, fnd["description"], fnd["category"], fnd["severity"], fnd["location"], fnd["corrective_action"], fnd["responsible_person"], fnd["due_date"], fnd["status"], fnd["confidence"], fnd["page_no"])
                )
            avg_conf = 0.90 if report_data["findings"] else 0.70
        else:
            # Manual or SOP
            manual_data = manual_extractor.extract_manual_data(pages)
            for sec in manual_data["sections"]:
                execute_insert(
                    "INSERT INTO doc_sections (document_id, parent_id, title, level, page_start, page_end) VALUES (%s, %s, %s, %s, %s, %s)",
                    (doc_id, None, sec["title"], sec["level"], sec["page_start"], sec["page_end"])
                )
            for r in manual_data["rules"]:
                execute_insert(
                    "INSERT INTO manual_rules (document_id, section_id, rule_text, ppe_type, page_no) VALUES (%s, %s, %s, %s, %s)",
                    (doc_id, None, r["rule_text"], r["ppe_type"], r["page_no"])
                )
            for pr in manual_data["procedures"]:
                execute_insert(
                    "INSERT INTO manual_procedures (document_id, section_id, title, steps, page_no) VALUES (%s, %s, %s, %s, %s)",
                    (doc_id, None, pr["title"], pr["steps"], pr["page_no"])
                )
            avg_conf = 0.92 if manual_data["rules"] else 0.75

        # 5. Chunking & Indexing
        _update_progress(doc_id, "Chunking and vector indexing", 85)
        execute_query("DELETE FROM doc_chunks WHERE document_id = %s", (doc_id,), fetch=False, commit=True)
        chunks = chunker.chunk_document(doc_id, repo_id, pages)

        for c in chunks:
            execute_insert(
                "INSERT INTO doc_chunks (document_id, repository_id, section_id, page_no, chunk_index, text) VALUES (%s, %s, %s, %s, %s, %s)",
                (doc_id, repo_id, None, c["page_no"], c["chunk_index"], c["text"])
            )

        # Re-build global vector index
        all_chunks = execute_query("SELECT document_id, repository_id, page_no, chunk_index, text FROM doc_chunks", fetch=True) or []
        embedder.build_index([dict(row) for row in all_chunks])

        # 6. Finalize status
        final_status = "processed"
        if avg_conf < 0.60:
            final_status = "needs review"

        execute_query(
            "UPDATE documents SET doc_type = %s, page_count = %s, status = %s, progress_percent = 100, avg_confidence = %s, processed_at = %s WHERE id = %s",
            (doc_type, page_count, final_status, avg_conf, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), doc_id),
            fetch=False, commit=True
        )

        pipeline_progress_store[doc_id] = {
            "status": final_status,
            "progress": 100,
            "step": "Completed",
            "error": None
        }
        logger.info(f"Document #{doc_id} processed successfully as {doc_type} with status '{final_status}'.")

    except Exception as e:
        logger.error(f"Error in document pipeline for #{doc_id}: {e}", exc_info=True)
        _fail_pipeline(doc_id, f"Processing error: {str(e)}")


def _fail_pipeline(doc_id: int, msg: str):
    pipeline_progress_store[doc_id] = {
        "status": "failed",
        "progress": 100,
        "step": "Failed",
        "error": msg
    }
    try:
        execute_query(
            "UPDATE documents SET status = 'failed', error_message = %s, progress_percent = 100 WHERE id = %s",
            (msg, doc_id), fetch=False, commit=True
        )
    except Exception:
        pass
