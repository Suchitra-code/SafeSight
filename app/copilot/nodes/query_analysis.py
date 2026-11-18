"""
Query Analysis Node for SafeSight Copilot (Mentor Requirement 3).
Parses user questions, resolves UI dashboard context, extracts entities,
identifies intent, and constructs a validated QueryPlan.
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Any
from app.copilot.events import traced
from app.copilot.schemas import QueryPlan


@traced("query_analysis")
def query_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """Analyzes the user question and returns a QueryPlan."""
    question = state.get("question", "").strip()
    ui_context = state.get("ui_context", {})
    history = state.get("history", [])

    q_lower = question.lower()

    # 1. Intent Detection
    if not question or len(question) < 2:
        plan = QueryPlan(
            intent="smalltalk",
            rewritten_question="Hello",
            clarifying_question="Hello! How can I assist you with site safety, PPE compliance, or manuals today?"
        )
        return {"plan": plan.model_dump(), "summary": "Detected empty or greeting intent"}

    if any(q_lower.startswith(g) for g in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        plan = QueryPlan(
            intent="smalltalk",
            rewritten_question=question,
            clarifying_question="Greetings! Ask me any question regarding camera violations, zone compliance, or safety manuals."
        )
        return {"plan": plan.model_dump(), "summary": "Detected smalltalk greeting"}

    if any(k in q_lower for k in ["weather", "sports", "recipe", "stock price", "movie", "bitcoin"]):
        plan = QueryPlan(
            intent="out_of_scope",
            rewritten_question=question
        )
        return {"plan": plan.model_dump(), "summary": "Detected out-of-scope question"}

    if any(k in q_lower for k in ["investigate", "launch investigation", "audit run"]):
        plan = QueryPlan(
            intent="investigate",
            rewritten_question=question,
            needs_visual=True
        )
        return {"plan": plan.model_dump(), "summary": "Detected workflow investigation request"}

    # 2. Extract Entities
    entities = {}

    # Zones
    if "zone a" in q_lower or (ui_context.get("zone") == "Zone A" and "this zone" in q_lower):
        entities["zone"] = "Zone A"
    elif "zone b" in q_lower or (ui_context.get("zone") == "Zone B" and "this zone" in q_lower):
        entities["zone"] = "Zone B"
    elif "exit" in q_lower or "gate" in q_lower:
        entities["zone"] = "Exit Gate"
    elif ui_context.get("zone"):
        entities["zone"] = ui_context.get("zone")

    # Cameras
    cam_match = re.search(r'cam\s*0?(\d+)', q_lower)
    if cam_match:
        entities["camera"] = f"Cam 0{cam_match.group(1)}"
    elif ui_context.get("camera"):
        entities["camera"] = ui_context.get("camera")

    # PPE Types & Violations
    if "helmet" in q_lower or "hardhat" in q_lower or "head" in q_lower:
        entities["violation_type"] = "Hardhat"
        entities["ppe_type"] = "Hardhat"
    elif "vest" in q_lower or "jacket" in q_lower:
        entities["violation_type"] = "Safety Vest"
        entities["ppe_type"] = "Safety Vest"
    elif "goggle" in q_lower or "glasses" in q_lower or "eye" in q_lower:
        entities["violation_type"] = "Goggles"
        entities["ppe_type"] = "Goggles"

    # Severity
    if "high" in q_lower or "critical" in q_lower:
        entities["severity"] = "HIGH"
    elif "medium" in q_lower:
        entities["severity"] = "MEDIUM"

    # Specific violation ID
    id_match = re.search(r'(?:violation|incident|id)\s*#?\s*(\d+)', q_lower)
    if id_match:
        entities["violation_id"] = int(id_match.group(1))

    # Date range calculations
    now = datetime.now(tz=None)  # local time; timezone-aware in production
    if "today" in q_lower:
        entities["date_from"] = now.strftime("%Y-%m-%d 00:00:00")
        entities["date_to"] = now.strftime("%Y-%m-%d 23:59:59")
    elif "yesterday" in q_lower:
        yesterday = now - timedelta(days=1)
        entities["date_from"] = yesterday.strftime("%Y-%m-%d 00:00:00")
        entities["date_to"] = yesterday.strftime("%Y-%m-%d 23:59:59")
    elif "7 days" in q_lower or "past week" in q_lower or "this week" in q_lower:
        entities["date_from"] = (now - timedelta(days=7)).strftime("%Y-%m-%d 00:00:00")
        entities["date_to"] = now.strftime("%Y-%m-%d 23:59:59")
    elif "30 days" in q_lower or "this month" in q_lower:
        entities["date_from"] = (now - timedelta(days=30)).strftime("%Y-%m-%d 00:00:00")
        entities["date_to"] = now.strftime("%Y-%m-%d 23:59:59")

    # Intent routing: Document vs Visual vs Both
    has_doc_keywords = any(k in q_lower for k in [
        "manual", "policy", "sop", "rule", "standard", "procedure", "penalty", "mandate", "report"
    ])
    has_vis_keywords = any(k in q_lower for k in [
        "camera", "detected", "saw", "see", "caught", "violation", "infraction", "trend",
        "how many", "zone", "feed", "snapshot", "live", "compliance"
    ])

    if has_doc_keywords and not has_vis_keywords:
        intent = "document"
        needs_doc = True
        needs_vis = False
    elif has_vis_keywords and not has_doc_keywords:
        intent = "visual"
        needs_doc = False
        needs_vis = True
    else:
        intent = "both"
        needs_doc = True
        needs_vis = True

    # Standalone normalized English question
    rewritten = question
    if "here" in q_lower and entities.get("zone"):
        rewritten = rewritten.replace("here", f"in {entities['zone']}")
    if "this zone" in q_lower and entities.get("zone"):
        rewritten = rewritten.replace("this zone", entities["zone"])

    plan = QueryPlan(
        intent=intent,
        needs_visual=needs_vis,
        needs_document=needs_doc,
        entities=entities,
        rewritten_question=rewritten,
        language="en",
        confidence=0.95
    )

    summary_text = f"Intent: {intent} (Visual: {needs_vis}, Doc: {needs_doc}, Entities: {list(entities.keys())})"
    return {
        "plan": plan.model_dump(),
        "summary": summary_text
    }
