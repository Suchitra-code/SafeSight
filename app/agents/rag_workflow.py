
from typing import TypedDict, List
from langgraph.graph import StateGraph, START, END


class WorkflowState(TypedDict):
    query: str
    needs_visual: bool
    visual_events: List[str]
    document_chunks: List[str]
    answer: str
    valid: bool
    retry_count: int


# 1. Query Analysis Node
def query_analysis(state: WorkflowState):
    query = state["query"].lower()

    return {
        "needs_visual": any(
            word in query
            for word in ["worker", "helmet", "vest", "violation", "image", "ppe"]
        )
    }


# 2. Visual Detection Retrieval Node
def visual_retrieval(state: WorkflowState):
    # TODO: Connect your existing visual event search here.
    events = state.get("visual_events", [])

    return {"visual_events": events}


# 3. Document Retrieval Node
def document_retrieval(state: WorkflowState):
    # TODO: Connect your existing RAG document retriever here.
    documents = state.get("document_chunks", [])

    return {"document_chunks": documents}


# 4. AI Answer Generation Node
def answer_generation(state: WorkflowState):
    visual = "\n".join(state.get("visual_events", []))
    documents = "\n".join(state.get("document_chunks", []))

    if not visual and not documents:
        answer = "No supporting information was found."
    else:
        answer = (
            f"Visual Detection Results:\n{visual or 'No visual events found.'}\n\n"
            f"Relevant Safety Documents:\n"
            f"{documents or 'No relevant document found.'}"
        )

    return {"answer": answer}


# 5. Answer Validation Node
def answer_validation(state: WorkflowState):
    has_evidence = bool(
        state.get("visual_events") or state.get("document_chunks")
    )
    return {
        "valid": has_evidence,
        "retry_count": state.get("retry_count", 0) + 1
    }


# Conditional routing
def validation_route(state: WorkflowState):
    if state["valid"]:
        return END
    if state["retry_count"] < 2:
        return "answer_generation"
    return END


# 6. Build LangGraph workflow
builder = StateGraph(WorkflowState)

builder.add_node("query_analysis", query_analysis)
builder.add_node("visual_retrieval", visual_retrieval)
builder.add_node("document_retrieval", document_retrieval)
builder.add_node("answer_generation", answer_generation)
builder.add_node("answer_validation", answer_validation)

builder.add_edge(START, "query_analysis")
builder.add_edge("query_analysis", "visual_retrieval")
builder.add_edge("visual_retrieval", "document_retrieval")
builder.add_edge("document_retrieval", "answer_generation")
builder.add_edge("answer_generation", "answer_validation")

builder.add_conditional_edges(
    "answer_validation",
    validation_route
)

workflow = builder.compile()


def run_workflow(query, visual_events=None, document_chunks=None):
    return workflow.invoke({
        "query": query,
        "needs_visual": False,
        "visual_events": visual_events or [],
        "document_chunks": document_chunks or [],
        "answer": "",
        "valid": False,
        "retry_count": 0
    })
