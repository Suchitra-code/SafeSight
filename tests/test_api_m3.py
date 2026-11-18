import unittest
import json
from app import create_app
from app.db import execute_query


class TestMilestone3APIs(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"

    def test_health_api(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("overall", data)
        self.assertIn("components", data)
        self.assertIn("database", data["components"])
        self.assertIn("detector", data["components"])
        self.assertIn("langgraph", data["components"])

    def test_assistant_ask_api(self):
        payload = {
            "question": "What PPE is required for welding?",
            "session_id": "test_sess_001"
        }
        res = self.client.post("/api/assistant/ask", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertIn("confidence", data)

        # Test history retrieval
        hist_res = self.client.get("/api/assistant/history/test_sess_001")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.get_json()
        self.assertIn("messages", hist_data)

    def test_investigations_api(self):
        # 1. List runs
        list_res = self.client.get("/api/investigations/")
        self.assertEqual(list_res.status_code, 200)
        data = list_res.get_json()
        self.assertIn("items", data)

        # 2. Start a run
        rows = execute_query("SELECT id FROM violations LIMIT 1", fetch=True)
        if rows:
            v_id = rows[0]["id"]
            start_res = self.client.post(f"/api/investigations/start/{v_id}")
            self.assertEqual(start_res.status_code, 200)
            s_data = start_res.get_json()
            self.assertIn("run_id", s_data)
            run_id = s_data["run_id"]

            # 3. Get run status
            run_res = self.client.get(f"/api/investigations/{run_id}")
            self.assertEqual(run_res.status_code, 200)

    def test_explain_violation_api(self):
        rows = execute_query("SELECT id FROM violations LIMIT 1", fetch=True)
        if rows:
            v_id = rows[0]["id"]
            res = self.client.get(f"/api/violations/{v_id}/explain")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn("explanation", data)

    def test_pages_render(self):
        # Assistant page
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"

        res = self.client.get("/assistant")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"SafeSight Intelligence Assistant", res.data)

        # Investigations page
        res = self.client.get("/investigations")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Incident Investigations", res.data)


if __name__ == "__main__":
    unittest.main()
