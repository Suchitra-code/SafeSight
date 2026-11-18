"""
LangGraph Workflow Definition for SafeSight Copilot (Mentor Requirements 2, 8, 9).
Constructs the complete StateGraph with all nodes, conditional routing edges,
and provides get_graph_description() for live UI visualization.
"""
from typing import Dict, Any
from langgraph.graph import StateGraph, START, END

from app.copilot.state import CopilotState
from app.copilot.nodes.query_analysis import query_analysis
from app.copilot.nodes.visual_retrieval import visual_retrieval
from app.copilot.nodes.document_retrieval import document_retrieval
from app.copilot.nodes.evidence_check import evidence_check
from app.copilot.nodes.answer_generation import answer_generation
from app.copilot.nodes.answer_validation import answer_validation
from app.copilot.nodes.final_response import final_response
from app.copilot.nodes.support_nodes import (
    smalltalk_reply, refuse, clarify, no_evidence, safe_fallback, start_investigation
)
import config


# --- Routing Functions for Conditional Edges ---

def route_after_query_analysis(state: CopilotState) -> str:
    """Routes based on query intent identified in QueryPlan."""
    plan = state.get("plan", {})
    intent = plan.get("intent", "both")

    if intent == "smalltalk":
        return "smalltalk_reply"
    if intent == "out_of_scope":
        return "refuse"
    if intent == "needs_clarification":
        return "clarify"
    if intent == "investigate":
        return "start_investigation"
    if plan.get("needs_visual", False):
        return "visual_retrieval"
    if plan.get("needs_document", False):
        return "document_retrieval"
    return "visual_retrieval"


def route_after_visual(state: CopilotState) -> str:
    """Routes after visual retrieval: checks if documents are also needed."""
    plan = state.get("plan", {})
    if plan.get("needs_document", False):
        return "document_retrieval"
    return "evidence_check"


def route_after_evidence_check(state: CopilotState) -> str:
    """Routes based on whether usable evidence was located."""
    if state.get("has_usable_evidence", False):
        return "answer_generation"
    return "no_evidence"


def route_after_validation(state: CopilotState) -> str:
    """Evaluates validation score and handles retry loop or fallbacks."""
    val = state.get("validation", {})
    verdict = val.get("verdict", "pass")
    retries = state.get("retries", 0)

    if verdict == "pass":
        return "final_response"
    elif verdict == "revise" and retries < config.COPILOT_MAX_RETRIES:
        # Increment retry counter
        state["retries"] = retries + 1
        return "answer_generation"
    else:
        return "safe_fallback"


def build_graph():
    """Builds and compiles the complete SafeSight Copilot LangGraph workflow."""
    builder = StateGraph(CopilotState)

    # 1. Register All Nodes
    builder.add_node("query_analysis", query_analysis)
    builder.add_node("visual_retrieval", visual_retrieval)
    builder.add_node("document_retrieval", document_retrieval)
    builder.add_node("evidence_check", evidence_check)
    builder.add_node("answer_generation", answer_generation)
    builder.add_node("answer_validation", answer_validation)
    builder.add_node("final_response", final_response)

    # Support Nodes
    builder.add_node("smalltalk_reply", smalltalk_reply)
    builder.add_node("refuse", refuse)
    builder.add_node("clarify", clarify)
    builder.add_node("no_evidence", no_evidence)
    builder.add_node("safe_fallback", safe_fallback)
    builder.add_node("start_investigation", start_investigation)

    # 2. Add Edges & Conditional Routing
    builder.add_edge(START, "query_analysis")

    # Conditional Branch 1: Query Analysis -> Specialized Node
    builder.add_conditional_edges(
        "query_analysis",
        route_after_query_analysis,
        {
            "smalltalk_reply": "smalltalk_reply",
            "refuse": "refuse",
            "clarify": "clarify",
            "start_investigation": "start_investigation",
            "visual_retrieval": "visual_retrieval",
            "document_retrieval": "document_retrieval"
        }
    )

    # Conditional Branch 2: Visual -> Doc or Evidence Check
    builder.add_conditional_edges(
        "visual_retrieval",
        route_after_visual,
        {
            "document_retrieval": "document_retrieval",
            "evidence_check": "evidence_check"
        }
    )

    builder.add_edge("document_retrieval", "evidence_check")

    # Conditional Branch 3: Evidence Check -> Generation or No Evidence
    builder.add_conditional_edges(
        "evidence_check",
        route_after_evidence_check,
        {
            "answer_generation": "answer_generation",
            "no_evidence": "no_evidence"
        }
    )

    builder.add_edge("answer_generation", "answer_validation")

    # Conditional Branch 4: Validation -> Final, Retry, or Fallback
    builder.add_conditional_edges(
        "answer_validation",
        route_after_validation,
        {
            "final_response": "final_response",
            "answer_generation": "answer_generation",
            "safe_fallback": "safe_fallback"
        }
    )

    # Direct routes to final_response
    builder.add_edge("smalltalk_reply", "final_response")
    builder.add_edge("refuse", "final_response")
    builder.add_edge("clarify", "final_response")
    builder.add_edge("no_evidence", "final_response")
    builder.add_edge("start_investigation", "final_response")
    builder.add_edge("safe_fallback", "final_response")

    builder.add_edge("final_response", END)

    # Compile the graph
    graph = builder.compile()
    return graph


def get_graph_description() -> Dict[str, Any]:
    """
    Returns exact nodes and edges structure from the LangGraph graph
    to dynamically render the interactive pipeline visualization in Mission Control.
    """
    nodes = [
        {"id": "query_analysis", "label": "Query Analysis", "step": 1, "description": "Extracts intent, entities & dashboard filters"},
        {"id": "visual_retrieval", "label": "Visual Retrieval", "step": 2, "description": "Searches camera violations & computes facts"},
        {"id": "document_retrieval", "label": "Document Retrieval", "step": 3, "description": "Hybrid search over safety manuals & SOPs"},
        {"id": "evidence_check", "label": "Evidence Check", "step": 4, "description": "Validates minimum score & relevance threshold"},
        {"id": "answer_generation", "label": "Answer Generation", "step": 5, "description": "Produces grounded AnswerCard with citations"},
        {"id": "answer_validation", "label": "Answer Validation", "step": 6, "description": "Trust Meter checks (citations, numbers, safety)"},
        {"id": "final_response", "label": "Final Response", "step": 7, "description": "Persists run & delivers structured response"},
        # Branch/Support nodes
        {"id": "smalltalk_reply", "label": "Smalltalk", "step": 2, "description": "Handles greetings & questions"},
        {"id": "refuse", "label": "Refusal", "step": 2, "description": "Rejects out-of-scope queries"},
        {"id": "clarify", "label": "Clarification", "step": 2, "description": "Prompts for missing query details"},
        {"id": "no_evidence", "label": "No Evidence", "step": 5, "description": "Advises user when no records match"},
        {"id": "safe_fallback", "label": "Safe Fallback", "step": 6, "description": "Safe extractive output on low trust"},
        {"id": "start_investigation", "label": "Investigation", "step": 2, "description": "Hands off to LangGraph investigation"}
    ]

    edges = [
        {"from": "START", "to": "query_analysis"},
        {"from": "query_analysis", "to": "visual_retrieval", "conditional": True, "condition": "needs_visual"},
        {"from": "query_analysis", "to": "document_retrieval", "conditional": True, "condition": "document_only"},
        {"from": "query_analysis", "to": "smalltalk_reply", "conditional": True, "condition": "smalltalk"},
        {"from": "query_analysis", "to": "refuse", "conditional": True, "condition": "out_of_scope"},
        {"from": "query_analysis", "to": "clarify", "conditional": True, "condition": "needs_clarification"},
        {"from": "query_analysis", "to": "start_investigation", "conditional": True, "condition": "investigate"},
        {"from": "visual_retrieval", "to": "document_retrieval", "conditional": True, "condition": "needs_document"},
        {"from": "visual_retrieval", "to": "evidence_check", "conditional": True, "condition": "visual_only"},
        {"from": "document_retrieval", "to": "evidence_check"},
        {"from": "evidence_check", "to": "answer_generation", "conditional": True, "condition": "evidence_ok"},
        {"from": "evidence_check", "to": "no_evidence", "conditional": True, "condition": "no_usable_evidence"},
        {"from": "answer_generation", "to": "answer_validation"},
        {"from": "answer_validation", "to": "final_response", "conditional": True, "condition": "score >= 80"},
        {"from": "answer_validation", "to": "answer_generation", "conditional": True, "condition": "revise & retries left"},
        {"from": "answer_validation", "to": "safe_fallback", "conditional": True, "condition": "fail or retries used"},
        {"from": "smalltalk_reply", "to": "final_response"},
        {"from": "refuse", "to": "final_response"},
        {"from": "clarify", "to": "final_response"},
        {"from": "no_evidence", "to": "final_response"},
        {"from": "safe_fallback", "to": "final_response"},
        {"from": "start_investigation", "to": "final_response"},
        {"from": "final_response", "to": "END"}
    ]

    return {
        "nodes": nodes,
        "edges": edges,
        "langgraph_version": config.LANGGRAPH_VERSION
    }
