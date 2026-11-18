import pytest
from app.copilot.graph import build_graph, get_graph_description


def test_build_graph_structure():
    graph = build_graph()
    assert graph is not None


def test_node_function_mapping():
    desc = get_graph_description()
    nodes = desc["nodes"]
    assert len(nodes) >= 10

    # Ensure every core node has a mapped function
    core_ids = {"query_analysis", "visual_retrieval", "document_retrieval", "evidence_check", "answer_generation", "answer_validation", "final_response"}
    present_ids = {n["id"] for n in nodes}
    assert core_ids.issubset(present_ids)


def test_conditional_routing():
    graph = build_graph()
    # Test execution for smalltalk query
    state = {
        "run_id": "test_smalltalk_run",
        "question": "Hello Copilot",
        "ui_context": {},
        "retries": 0,
        "validator_feedback": [],
        "route": [],
        "trace": []
    }
    final = graph.invoke(state)
    assert "smalltalk_reply" in final["route"]
    assert "final_response" in final["route"]
