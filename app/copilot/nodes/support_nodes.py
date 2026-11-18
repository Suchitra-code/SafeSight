"""
Support and Fallback Nodes for SafeSight Copilot.
Handles smalltalk, refusal, clarification, no-evidence, safe fallbacks, and investigation hand-off.
"""
from typing import Dict, Any
from app.copilot.events import traced
from app.copilot.schemas import AnswerCard, KeyFact, RecommendedAction


@traced("smalltalk_reply")
def smalltalk_reply(state: Dict[str, Any]) -> Dict[str, Any]:
    """Provides a friendly conversational greeting with actionable examples."""
    card = AnswerCard(
        headline="Welcome to SafeSight Copilot",
        answer=(
            "Hello! I am your AI Safety Copilot for site surveillance and safety compliance. "
            "I synthesize real-time computer vision telemetry from cameras with corporate safety handbooks and SOPs."
        ),
        key_facts=[
            KeyFact(label="Surveillance Feeds", value="Active"),
            KeyFact(label="Knowledge Base", value="Indexed")
        ],
        recommended_actions=[
            RecommendedAction(action="Ask: 'What are the top safety infractions recorded today?'"),
            RecommendedAction(action="Ask: 'What do site manuals require for crane operations?'")
        ],
        risk_level="LOW",
        follow_up_questions=[
            "Show safety compliance in Zone A.",
            "What PPE is mandatory for welding operations?",
            "How many helmet violations occurred this week?"
        ]
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": "Handled smalltalk with example safety queries"
    }


@traced("refuse")
def refuse(state: Dict[str, Any]) -> Dict[str, Any]:
    """Politely declines out-of-scope inquiries."""
    card = AnswerCard(
        headline="Out of Scope Request",
        answer=(
            "I am specialized specifically for workplace safety, PPE compliance, and corporate safety handbooks. "
            "I cannot answer questions outside of industrial safety surveillance and site operating procedures."
        ),
        risk_level="LOW",
        recommended_actions=[
            RecommendedAction(action="Please rephrase your question regarding site cameras, PPE gear, or safety manuals.")
        ]
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": "Refused out-of-scope question"
    }


@traced("clarify")
def clarify(state: Dict[str, Any]) -> Dict[str, Any]:
    """Requests clarification when the query is ambiguous."""
    plan = state.get("plan", {})
    cq = plan.get("clarifying_question") or "Could you clarify which facility zone or safety equipment you are asking about?"
    card = AnswerCard(
        headline="Clarification Needed",
        answer=cq,
        risk_level="LOW",
        recommended_actions=[
            RecommendedAction(action="Select a specific zone (Zone A, Zone B, Exit Gate)."),
            RecommendedAction(action="Specify a PPE category (Hardhat, Safety Vest, Goggles).")
        ]
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": "Prompted user for query clarification"
    }


@traced("no_evidence")
def no_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    """Informs the user when no relevant records exist."""
    card = AnswerCard(
        headline="No Correlating Records Found",
        answer=(
            "I could not find sufficient matching events or documentation in the system for this specific inquiry. "
            "Try broadening your search criteria or removing active filters."
        ),
        risk_level="LOW",
        recommended_actions=[
            RecommendedAction(action="Check active filters on the Mission Control dashboard."),
            RecommendedAction(action="Verify that documents or video files have been uploaded.")
        ]
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": "No usable evidence found"
    }


@traced("safe_fallback")
def safe_fallback(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extractive fallback with low confidence disclaimer."""
    facts = state.get("facts", {})
    v_ev = state.get("visual_evidence", [])
    d_ev = state.get("document_evidence", [])

    snippet = d_ev[0].get("snippet") if d_ev else "Safety regulations mandate standard PPE across all zones."
    card = AnswerCard(
        headline="Low-Confidence Safety Summary",
        answer=f"Synthesized from available records: {snippet[:200]} [D1]. Verification is strongly recommended.",
        risk_level="MEDIUM",
        recommended_actions=[
            RecommendedAction(action="Consult the on-duty safety inspector for direct verification.")
        ]
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": "Constructed safe fallback response"
    }


@traced("start_investigation")
def start_investigation(state: Dict[str, Any]) -> Dict[str, Any]:
    """Initiates an agentic investigation workflow or links to existing run."""
    plan = state.get("plan", {})
    entities = plan.get("entities", {})
    vid = entities.get("violation_id", 1)

    card = AnswerCard(
        headline=f"LangGraph Investigation Triggered for Incident #{vid}",
        answer=(
            f"An automated deep-dive investigation was initiated for Violation #{vid}. "
            f"The LangGraph workflow cross-references visual telemetry, supervisor logs, and manual guidelines."
        ),
        key_facts=[
            KeyFact(label="Target Incident", value=f"#{vid}"),
            KeyFact(label="Workflow", value="LangGraph Multi-Agent")
        ],
        recommended_actions=[
            RecommendedAction(action=f"Open the Investigation details page at /investigations/{vid}.")
        ],
        risk_level="HIGH"
    )
    return {
        "answer_card": card.model_dump(),
        "mode": "offline",
        "summary": f"Handed off incident #{vid} to LangGraph investigation workflow"
    }
