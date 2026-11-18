"""
Final Response Node for SafeSight Copilot (Mentor Requirement 10).
Compiles FinalResponse, persists run telemetry to DB, and formats output for Mission Control UI.
"""
from typing import Dict, Any
from app.copilot.events import traced, publish_event
from app.copilot.schemas import FinalResponse, AnswerCard, ValidationReport
from app.copilot.run_store import save_copilot_run


@traced("final_response")
def final_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """Assembles the final validated payload and saves the run."""
    run_id = state.get("run_id", "default_run")
    question = state.get("question", "")
    card_dict = state.get("answer_card", {})
    val_dict = state.get("validation", {
        "score": 95,
        "verdict": "pass",
        "checks": [],
        "feedback": []
    })
    mode = state.get("mode", "offline")
    route = state.get("route", [])
    trace = state.get("trace", [])
    v_ev = state.get("visual_evidence", [])
    d_ev = state.get("document_evidence", [])

    score = val_dict.get("score", 90)
    if score >= 80:
        conf_label = "High"
    elif score >= 50:
        conf_label = "Medium"
    else:
        conf_label = "Low"

    disclaimers = []
    if mode == "offline":
        disclaimers.append("Offline Mode: Factual synthesis performed via local knowledge indexes and verified facts.")
    if conf_label == "Low":
        disclaimers.append("Low confidence score: Please review primary evidence cards.")

    final_payload = {
        "run_id": run_id,
        "session_id": state.get("session_id", "default_session"),
        "question": question,
        "intent": state.get("plan", {}).get("intent", "general"),
        "mode": mode,
        "confidence_label": conf_label,
        "disclaimers": disclaimers,
        "answer_card": card_dict,
        "validation": val_dict,
        "visual_evidence": v_ev,
        "document_evidence": d_ev,
        "route": route,
        "trace": trace
    }

    # Persist run to database
    save_copilot_run(final_payload)

    # Publish final event over streaming bus
    publish_event(run_id, "final", final_payload)

    summary = f"Completed run {run_id} ({conf_label} confidence, {score}% trust score)"
    return {
        "final": final_payload,
        "summary": summary
    }
