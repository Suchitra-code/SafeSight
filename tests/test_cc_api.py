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


def test_command_center_page(client):
    res = client.get("/command-center")
    assert res.status_code == 200
    assert b"Mission Control" in res.data


def test_command_center_kpis_api(client):
    res = client.get("/api/command-center/kpis")
    assert res.status_code == 200
    data = res.get_json()
    assert "compliance_rate" in data
    assert "workers_detected" in data


def test_command_center_heatmap_and_trends(client):
    res = client.get("/api/command-center/heatmap")
    assert res.status_code == 200
    assert "matrix" in res.get_json()

    res_t = client.get("/api/command-center/trends")
    assert res_t.status_code == 200
    assert "compliance" in res_t.get_json()


def test_command_center_zones(client):
    res = client.get("/api/command-center/zones")
    assert res.status_code == 200
    assert "zones" in res.get_json()
