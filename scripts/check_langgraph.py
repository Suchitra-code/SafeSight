"""
Verification script for LangGraph installation and compilation.
Builds a 3-node toy graph with conditional routing, compiles it,
and asserts execution.
"""
import sys
from typing import TypedDict
import langgraph
from langgraph.graph import StateGraph, START, END


class ToyState(TypedDict):
    value: int
    path: str


def node_start(state: ToyState) -> dict:
    return {"value": state["value"] + 1, "path": "start"}


def node_high(state: ToyState) -> dict:
    return {"path": state["path"] + "->high"}


def node_low(state: ToyState) -> dict:
    return {"path": state["path"] + "->low"}


def route_decision(state: ToyState) -> str:
    if state["value"] > 5:
        return "high"
    return "low"


def test_toy_graph():
    builder = StateGraph(ToyState)
    builder.add_node("start_node", node_start)
    builder.add_node("high_node", node_high)
    builder.add_node("low_node", node_low)

    builder.add_edge(START, "start_node")
    builder.add_conditional_edges(
        "start_node",
        route_decision,
        {"high": "high_node", "low": "low_node"}
    )
    builder.add_edge("high_node", END)
    builder.add_edge("low_node", END)

    graph = builder.compile()

    # Test execution
    res1 = graph.invoke({"value": 10, "path": ""})
    assert res1["path"] == "start->high", f"Unexpected path: {res1['path']}"

    res2 = graph.invoke({"value": 2, "path": ""})
    assert res2["path"] == "start->low", f"Unexpected path: {res2['path']}"

    import importlib.metadata
    try:
        version = importlib.metadata.version("langgraph")
    except Exception:
        version = getattr(langgraph, "__version__", "unknown")
    print(f"LangGraph v{version} verified successfully! Toy graph compiled and passed.")
    return version


if __name__ == "__main__":
    try:
        ver = test_toy_graph()
        sys.exit(0)
    except Exception as e:
        print(f"LangGraph check failed: {e}", file=sys.stderr)
        sys.exit(1)
