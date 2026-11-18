import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
        yield c


def test_copilot_graph_endpoint(client):
    res = client.get("/api/copilot/graph")
    assert res.status_code == 200
    data = res.get_json()
    assert "nodes" in data
    assert "edges" in data


def test_copilot_suggestions_endpoint(client):
    res = client.get("/api/copilot/suggestions")
    assert res.status_code == 200
    data = res.get_json()
    assert "suggestions" in data
    assert len(data["suggestions"]) > 0


def test_copilot_ask_and_history(client):
    res = client.post("/api/copilot/ask", json={
        "question": "What are the rules for safety vests?"
    })
    assert res.status_code == 202
    data = res.get_json()
    assert data["success"] is True
    assert "run_id" in data

    # Check history endpoint
    h_res = client.get("/api/copilot/history")
    assert h_res.status_code == 200
