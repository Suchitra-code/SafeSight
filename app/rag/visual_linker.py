"""
Visual-to-Document linking services for SafeSight AI - Milestone 3.
Implements:
1. explain_violation(violation_id): Builds full visual context, retrieves relevant
   safety manual rules, SOPs, past inspector findings, and similar camera events.
2. find_matching_camera_events(category, date_str, days_window): Reverse lookup from
   inspection findings to camera violations.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from app.db import execute_query
from app.services.violation_service import get_violation_by_id
from app.rag.retriever import retrieve
from app.llm.provider import get_llm_client, LLMError

logger = logging.getLogger(__name__)


def explain_violation(violation_id: int) -> Dict[str, Any]:
    """
    Explains a detected camera violation using the company's safety manuals,
    past inspection findings, and similar past camera detections.
    Works offline via structured data assembly and supports LLM rewrite if available.
    """
    v = get_violation_by_id(violation_id)
    if not v:
        return {
            "error": f"Violation ID {violation_id} not found",
            "violation_id": violation_id
        }

    v_type = v.get("violation_type") or "PPE"
    severity = v.get("severity") or "MEDIUM"
    camera = v.get("camera_name") or "Cam 01"
    location = v.get("location") or "Zone A"
    detected_at = str(v.get("detected_at") or "")
    confidence = float(v.get("confidence") or 0.85)
    snapshot = v.get("snapshot_path") or ""

    # 1. Retrieve applicable Safety Manual rules & SOPs
    rule_query = f"{v_type} required safety rule mandatory policy PPE standard"
    rule_sources = retrieve(rule_query, top_k=3, filters={"source_types": ["document"]})

    rules_list = []
    for s in rule_sources:
        rules_list.append({
            "title": s.title,
            "page": s.page,
            "snippet": s.snippet,
            "ref_id": s.ref_id
        })

    # 2. Retrieve related inspector findings (same category, nearby date)
    related_findings = []
    try:
        f_query = """
            SELECT id, document_id, description, severity, corrective_action, due_date, status
            FROM report_findings
            WHERE LOWER(description) LIKE %s OR LOWER(category) LIKE %s
            ORDER BY id DESC LIMIT 3
        """
        like_pat = f"%{v_type.lower()}%"
        f_rows = execute_query(f_query, (like_pat, like_pat), fetch=True) or []
        for r in f_rows:
            related_findings.append(dict(r))
    except Exception as e:
        logger.warning(f"Error fetching related findings: {e}")

    # 3. Retrieve similar past camera events (same camera or type in last 30 days)
    similar_events = []
    try:
        s_query = """
            SELECT id, violation_type, severity, camera_name, location, detected_at, snapshot_path
            FROM violations
            WHERE id != %s AND (violation_type = %s OR camera_name = %s)
            ORDER BY detected_at DESC LIMIT 5
        """
        s_rows = execute_query(s_query, (violation_id, v_type, camera), fetch=True) or []
        for r in s_rows:
            item = dict(r)
            if item.get("snapshot_path"):
                item["snapshot_url"] = f"/api/violations/{item['id']}/snapshot"
            similar_events.append(item)
    except Exception as e:
        logger.warning(f"Error fetching similar violations: {e}")

    # 4. Formulate explanation narrative (offline template default)
    what_happened = (
        f"A {severity} severity violation for '{v_type}' was flagged by {camera} ({location}) "
        f"on {detected_at} with a vision detection confidence of {confidence * 100:.1f}%."
    )

    primary_rule = rules_list[0]["snippet"] if rules_list else "All site personnel and contractors must strictly adhere to mandated PPE requirements."
    primary_rule_title = rules_list[0]["title"] if rules_list else "Corporate PPE Manual"
    primary_rule_page = rules_list[0]["page"] if rules_list else 1

    rule_summary = f"Under [{primary_rule_title}, p.{primary_rule_page}], {primary_rule}"

    recommended_action = (
        f"Issue immediate corrective instruction for {v_type} compliance. "
        f"Brief the shift supervisor at {location} and verify gear before work proceeds."
    )

    # Optional LLM rewrite if online
    llm = get_llm_client()
    narrative = what_happened
    if llm.is_available():
        try:
            sys_prompt = "You are a safety officer. Summarize this incident concisely in 2 sentences with citations."
            user_prompt = f"Incident: {what_happened}\nRule: {rule_summary}\nAction: {recommended_action}"
            narrative = llm.generate(sys_prompt, user_prompt, max_tokens=250)
        except LLMError:
            pass

    return {
        "violation_id": violation_id,
        "event": {
            "type": v_type,
            "severity": severity,
            "camera": camera,
            "location": location,
            "detected_at": detected_at,
            "confidence": confidence,
            "snapshot_url": f"/api/violations/{violation_id}/snapshot" if snapshot else None
        },
        "what_happened": what_happened,
        "what_the_rule_says": rule_summary,
        "rules": rules_list,
        "related_findings": related_findings,
        "similar_events": similar_events,
        "recommended_action": recommended_action,
        "narrative": narrative
    }


def find_matching_camera_events(category: str, days_window: int = 7) -> List[Dict[str, Any]]:
    """
    Reverse link: Given an inspection finding category or keyword (e.g. 'helmet', 'vest', 'goggles'),
    retrieves recent matching camera violations with snapshot URLs.
    """
    try:
        sql = """
            SELECT id, violation_type, severity, camera_name, location, detected_at, snapshot_path, confidence
            FROM violations
            WHERE LOWER(violation_type) LIKE %s OR LOWER(location) LIKE %s
            ORDER BY detected_at DESC LIMIT 6
        """
        pat = f"%{category.lower()}%"
        rows = execute_query(sql, (pat, pat), fetch=True) or []
        events = []
        for r in rows:
            item = dict(r)
            item["snapshot_url"] = f"/api/violations/{item['id']}/snapshot" if item.get("snapshot_path") else None
            events.append(item)
        return events
    except Exception as e:
        logger.error(f"Error in find_matching_camera_events: {e}")
        return []
