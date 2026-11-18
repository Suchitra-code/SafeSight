"""
CopilotState typed dict and reducers for SafeSight Copilot (Milestone 4).
Uses operator.add for list accumulators (route, trace, visual_evidence, document_evidence).
Guarantees full JSON-serializability across state nodes.
"""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
import operator


class CopilotState(TypedDict, total=False):
    run_id: str
    session_id: str
    question: str
    image_path: Optional[str]
    ui_context: Dict[str, Any]
    history: List[Dict[str, str]]
    language: str
    plan: Dict[str, Any]
    visual_evidence: Annotated[List[Dict[str, Any]], operator.add]
    document_evidence: Annotated[List[Dict[str, Any]], operator.add]
    facts: Dict[str, Any]
    answer_card: Dict[str, Any]
    validation: Dict[str, Any]
    retries: int
    validator_feedback: List[str]
    route: Annotated[List[str], operator.add]
    trace: Annotated[List[Dict[str, Any]], operator.add]
    final: Dict[str, Any]
    mode: str  # 'llm' | 'offline'
    error: Optional[str]
