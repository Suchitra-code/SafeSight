import pytest
from app.copilot.state import CopilotState
from app.copilot.events import register_run, get_run_queue, cleanup_run, publish_event, traced


def test_copilot_state_structure():
    state: CopilotState = {
        "run_id": "test_run_1",
        "session_id": "test_session",
        "question": "What are the rules for hardhats?",
        "ui_context": {"zone": "Zone A"},
        "history": [],
        "language": "en",
        "route": ["query_analysis"],
        "trace": [{"node": "query_analysis", "duration_ms": 12.5, "summary": "OK"}],
        "mode": "offline"
    }
    assert state["run_id"] == "test_run_1"
    assert len(state["route"]) == 1
    assert state["route"][0] == "query_analysis"


def test_event_bus_and_traced_decorator():
    run_id = "test_event_run"
    q = register_run(run_id)
    assert q is not None
    assert get_run_queue(run_id) is q

    @traced("sample_node")
    def sample_node(state):
        return {"summary": "Executed sample node"}

    test_state = {"run_id": run_id, "question": "test"}
    result = sample_node(test_state)

    assert "route" in result
    assert result["route"] == ["sample_node"]
    assert len(result["trace"]) == 1
    assert result["trace"][0]["node"] == "sample_node"

    # Verify event published into queue
    ev = q.get_nowait()
    assert ev["event_type"] == "node_started"
    ev2 = q.get_nowait()
    assert ev2["event_type"] == "node_finished"

    cleanup_run(run_id)
    assert get_run_queue(run_id) is None
