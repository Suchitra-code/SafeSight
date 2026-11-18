"""
Investigation Workflow Graph for SafeSight AI - Milestone 3.
Implements the multi-step LangGraph agentic workflow for incident investigation
with human-in-the-loop review and approval.
"""
import logging
from typing import Dict, Any, List, Optional
import sqlite3

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

import config
from app.db import execute_query, execute_insert
from app.agents.state import InvestigationState
from app.agents.risk import compute_risk
from app.agents.tools import (
    get_violation, search_knowledge, find_similar_events,
    find_related_findings, update_violation_status, generate_incident_pdf
)
from app.llm.provider import get_llm_client, LLMError
from app.llm.prompts import INVESTIGATION_RECOMMENDATION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def log_agent_step(run_id: str, node_name: str, in_summary: str, out_summary: str, status: str = "completed", error: Optional[str] = None):
    try:
        execute_insert(
            """INSERT INTO agent_steps (run_id, node_name, input_summary, output_summary, status, error_message)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (run_id, node_name, str(in_summary)[:240], str(out_summary)[:240], status, error)
        )
    except Exception as e:
        logger.warning(f"Failed to log agent step {node_name}: {e}")


def update_run_db(run_id: str, **fields):
    if not fields:
        return
    try:
        set_clauses = [f"{k} = %s" for k in fields.keys()]
        sql = f"UPDATE investigation_runs SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE run_id = %s"
        params = list(fields.values()) + [run_id]
        execute_query(sql, tuple(params), commit=True)
    except Exception as e:
        logger.warning(f"Failed to update investigation_runs for {run_id}: {e}")


# --- Nodes ---

def load_event(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    v_id = state.get("violation_id", 0)
    event = get_violation(v_id)
    if not event:
        err = f"Violation #{v_id} not found."
        log_agent_step(run_id, "load_event", f"v_id={v_id}", "Not found", status="failed", error=err)
        update_run_db(run_id, status="failed", current_node="load_event")
        return {"error": err, "status": "failed", "current_node": "load_event", "trace": ["load_event (failed)"]}

    camera = event.get('camera_name') or event.get('camera') or 'Unknown'
    out_msg = f"Loaded {event.get('violation_type')} on {camera}"
    log_agent_step(run_id, "load_event", f"v_id={v_id}", out_msg)
    update_run_db(run_id, current_node="load_event", summary=out_msg)
    return {
        "event": event,
        "current_node": "load_event",
        "trace": ["load_event"]
    }


def build_visual_context(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    event = state.get("event", {})
    context = {
        "camera": event.get("camera_name") or event.get("camera", "Unknown"),
        "zone": event.get("location", "Facility"),
        "detected_at": str(event.get("detected_at")),
        "violation_type": event.get("violation_type", "PPE Infraction"),
        "severity": event.get("severity", "MEDIUM"),
        "snapshot_path": event.get("snapshot_path", "")
    }
    out_msg = f"Visual context assembled for {context['camera']} in {context['zone']}"
    log_agent_step(run_id, "build_visual_context", str(event.get("violation_type")), out_msg)
    update_run_db(run_id, current_node="build_visual_context")
    return {
        "visual_context": context,
        "current_node": "build_visual_context",
        "trace": ["build_visual_context"]
    }


def retrieve_rules(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    event = state.get("event", {})
    v_type = event.get("violation_type", "safety")
    query = f"PPE requirements and mandatory standards for {v_type}"
    sources = search_knowledge(query, filters={"source_types": ["document"]})
    out_msg = f"Retrieved {len(sources)} policy/manual rules"
    log_agent_step(run_id, "retrieve_rules", query, out_msg)
    update_run_db(run_id, current_node="retrieve_rules")
    return {
        "rules": sources,
        "current_node": "retrieve_rules",
        "trace": ["retrieve_rules"]
    }


def find_similar_events_node(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    v_id = state.get("violation_id", 0)
    similars = find_similar_events(v_id, days=14)
    out_msg = f"Found {len(similars)} repeat events in past 14 days"
    log_agent_step(run_id, "find_similar_events", f"v_id={v_id}", out_msg)
    update_run_db(run_id, current_node="find_similar_events")
    return {
        "similar_events": similars,
        "current_node": "find_similar_events",
        "trace": ["find_similar_events"]
    }


def find_related_findings_node(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    event = state.get("event", {})
    v_type = event.get("violation_type", "")
    # Check open findings in database
    findings = find_related_findings(v_type, "2020-01-01", "2030-01-01")
    out_msg = f"Found {len(findings)} open inspector findings matching {v_type}"
    log_agent_step(run_id, "find_related_findings", v_type, out_msg)
    update_run_db(run_id, current_node="find_related_findings")
    return {
        "related_findings": findings,
        "current_node": "find_related_findings",
        "trace": ["find_related_findings"]
    }


def assess_risk(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    event = state.get("event", {})
    similars = state.get("similar_events", [])
    findings = state.get("related_findings", [])
    rules = state.get("rules", [])

    has_mandatory = any("mandatory" in str(r.get("snippet", "")).lower() for r in rules)
    score, level = compute_risk(
        violation_type=event.get("violation_type", ""),
        severity=event.get("severity", "MEDIUM"),
        similar_count_7d=len(similars),
        has_open_finding=len(findings) > 0,
        mandatory_rule=has_mandatory
    )
    out_msg = f"Risk Score: {score} -> Level: {level}"
    log_agent_step(run_id, "assess_risk", f"similars={len(similars)}, findings={len(findings)}", out_msg)
    update_run_db(run_id, risk_score=score, risk_level=level, current_node="assess_risk")
    return {
        "risk_score": score,
        "risk_level": level,
        "current_node": "assess_risk",
        "trace": ["assess_risk"]
    }


def recommend_actions(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    event = state.get("event", {})
    level = state.get("risk_level", "LOW")
    rules = state.get("rules", [])
    v_type = event.get("violation_type", "PPE Infraction")

    # Offline deterministic template first
    rule_summaries = [f"- {r.get('title', 'Manual')}: {r.get('snippet', '')[:100]}..." for r in rules[:2]]
    template_recs = (
        f"1. Immediate action: Issue mandatory safety briefing to personnel regarding {v_type} compliance.\n"
        f"2. Equipment audit: Inspect personal protective gear condition in zone {event.get('location', 'Site')}.\n"
        f"3. Policy reference: Adhere to verified site safety operating procedures."
    )
    if rule_summaries:
        template_recs += "\n\nReferenced Policies:\n" + "\n".join(rule_summaries)

    final_recs = template_recs
    llm = get_llm_client()
    if llm.is_available():
        try:
            prompt = (
                f"Incident: {v_type} on camera {event.get('camera')}. Risk Level: {level}.\n"
                f"Policy Chunks:\n{template_recs}\n\nDraft 3 concise, numbered corrective recommendations."
            )
            llm_out = llm.generate(INVESTIGATION_RECOMMENDATION_SYSTEM_PROMPT, prompt, max_tokens=300)
            if llm_out:
                final_recs = llm_out
        except Exception as e:
            logger.info(f"LLM recommendation fallback to template: {e}")

    summary = f"Identified {v_type} under {level} risk severity. Corrective workflow initiated."
    log_agent_step(run_id, "recommend_actions", f"level={level}", "Generated corrective recommendations")
    update_run_db(run_id, summary=summary, recommendations=final_recs, current_node="recommend_actions")

    return {
        "recommendations": final_recs,
        "current_node": "recommend_actions",
        "trace": ["recommend_actions"]
    }


def human_review(state: InvestigationState) -> Dict[str, Any]:
    """Interruption boundary. Supervisor decision is incorporated upon resume."""
    run_id = state.get("run_id", "")
    approval = state.get("approval") or {}
    decision = approval.get("decision", "approved")
    notes = approval.get("notes", "Reviewed by supervisor.")

    out_msg = f"Decision: {decision.upper()} - {notes}"
    log_agent_step(run_id, "human_review", "Supervisor sign-off", out_msg)
    update_run_db(run_id, approval_status=decision, supervisor_notes=notes, current_node="human_review")
    return {
        "current_node": "human_review",
        "trace": [f"human_review ({decision})"]
    }


def apply_decision(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    v_id = state.get("violation_id", 0)
    approval = state.get("approval") or {}
    decision = approval.get("decision", "approved")
    notes = approval.get("notes", "Actioned via investigation.")

    new_status = "verified" if decision == "approved" else "dismissed"
    update_violation_status(v_id, status=new_status, notes=notes, reviewed_by="AI Supervisor")
    out_msg = f"Violation #{v_id} status updated to {new_status}"
    log_agent_step(run_id, "apply_decision", f"v_id={v_id}", out_msg)
    update_run_db(run_id, current_node="apply_decision")
    return {
        "current_node": "apply_decision",
        "trace": ["apply_decision"]
    }


def generate_report_node(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    report_file = generate_incident_pdf(run_id)
    out_msg = f"PDF Report generated: {report_file}" if report_file else "PDF generation bypassed"
    log_agent_step(run_id, "generate_report", run_id, out_msg)
    update_run_db(run_id, report_path=report_file, current_node="generate_report")
    return {
        "report_path": report_file,
        "current_node": "generate_report",
        "trace": ["generate_report"]
    }


def finish(state: InvestigationState) -> Dict[str, Any]:
    run_id = state.get("run_id", "")
    log_agent_step(run_id, "finish", run_id, "Investigation completed successfully")
    update_run_db(run_id, status="completed", current_node="finish")
    return {
        "status": "completed",
        "current_node": "finish",
        "trace": ["finish"]
    }


# --- Build & Compile Graph ---

def create_investigation_graph(checkpointer=None):
    builder = StateGraph(InvestigationState)

    builder.add_node("load_event", load_event)
    builder.add_node("build_visual_context", build_visual_context)
    builder.add_node("retrieve_rules", retrieve_rules)
    builder.add_node("find_similar_events", find_similar_events_node)
    builder.add_node("find_related_findings", find_related_findings_node)
    builder.add_node("assess_risk", assess_risk)
    builder.add_node("recommend_actions", recommend_actions)
    builder.add_node("human_review", human_review)
    builder.add_node("apply_decision", apply_decision)
    builder.add_node("generate_report", generate_report_node)
    builder.add_node("finish", finish)

    builder.add_edge(START, "load_event")
    builder.add_edge("load_event", "build_visual_context")
    builder.add_edge("build_visual_context", "retrieve_rules")
    builder.add_edge("retrieve_rules", "find_similar_events")
    builder.add_edge("find_similar_events", "find_related_findings")
    builder.add_edge("find_related_findings", "assess_risk")
    builder.add_edge("assess_risk", "recommend_actions")
    builder.add_edge("recommend_actions", "human_review")
    builder.add_edge("human_review", "apply_decision")
    builder.add_edge("apply_decision", "generate_report")
    builder.add_edge("generate_report", "finish")
    builder.add_edge("finish", END)

    if checkpointer:
        return builder.compile(checkpointer=checkpointer, interrupt_before=["human_review"])
    return builder.compile()
