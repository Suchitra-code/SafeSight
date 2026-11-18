'''Typed state definitions for LangGraph workflows in SafeSight AI Milestone 3.

All states are TypedDicts so that static type checking works and LangGraph can
serialize them to SQLite via the checkpointer.
'''

from typing import TypedDict, List, Optional, Annotated
import operator

# ---------------------------------------------------------------------------
# Investigation workflow state
# ---------------------------------------------------------------------------
class InvestigationState(TypedDict, total=False):
    """State passed between nodes of the investigation graph.

    The keys correspond to data produced or consumed by each node.  ``trace``
    accumulates a readable log of visited nodes – the ``Annotated`` type with
    ``operator.add`` tells LangGraph to *append* to the existing list rather than
    overwriting it.
    """

    run_id: str
    violation_id: int
    event: dict
    visual_context: dict
    rules: List[dict]
    similar_events: List[dict]
    related_findings: List[dict]
    risk_score: int
    risk_level: str
    recommendations: str
    approval: Optional[dict]
    report_path: Optional[str]
    status: str
    current_node: str
    trace: Annotated[List[str], operator.add]
    error: Optional[str]

# ---------------------------------------------------------------------------
# Assistant (RAG) workflow state
# ---------------------------------------------------------------------------
class AssistantState(TypedDict, total=False):
    """State for the RAG assistant graph.

    ``history`` is a list of prior messages (role, content) to preserve the
    conversation context.  ``trace`` again uses ``Annotated`` for incremental
    logging.
    """

    session_id: str
    question: str
    intent: str
    filters: dict
    sources: List[dict]
    answer: str
    citations: List[dict]
    confidence: float
    history: Annotated[List[dict], operator.add]
    trace: Annotated[List[str], operator.add]
    error: Optional[str]
