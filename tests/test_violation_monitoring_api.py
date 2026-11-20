"""
Integration and API tests for Violation Monitoring:
- GET /api/violations (search, filters, pagination, schema, counts)
- PATCH /api/violations/<id>/status (auth check, status transition, audit logging)
- GET /violation-monitoring page route
"""
import unittest
from app import create_app
from app.db import execute_query


class TestViolationMonitoringApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            sess["user"] = "admin"

    def test_page_route_renders(self):
        """Test GET /violation-monitoring loads with 200 OK and contains key elements."""
        self._login()
        res = self.client.get("/violation-monitoring")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Violation Monitoring", html)
        self.assertIn("vmKpiTotal", html)
        self.assertIn("vmKpiPending", html)
        self.assertIn("vmKpiReviewed", html)
        self.assertIn("vmKpiResolved", html)
        self.assertIn("vmSearchInput", html)
        self.assertIn("vmTableBody", html)
        self.assertIn("vmModalBackdrop", html)

    def test_list_violations_api_default(self):
        """Test GET /api/violations returns 200, valid schema, and counts adding up to total."""
        self._login()
        res = self.client.get("/api/violations")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("ok"))
        self.assertIn("data", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("page_size", data)
        self.assertIn("counts", data)

        counts = data["counts"]
        self.assertIn("total", counts)
        self.assertIn("pending", counts)
        self.assertIn("reviewed", counts)
        self.assertIn("resolved", counts)
        # Check rule: pending + reviewed + resolved == total
        self.assertEqual(counts["pending"] + counts["reviewed"] + counts["resolved"], counts["total"])

        # Check item structure if violations exist
        if data["data"]:
            item = data["data"][0]
            self.assertIn("sno", item)
            self.assertIn("ui_status", item)
            self.assertIn("type_label", item)
            self.assertIn("date_formatted", item)
            self.assertIn("time_formatted", item)
            self.assertIn("location_display", item)

    def test_list_violations_search_filter(self):
        """Test search filter q parameter."""
        self._login()
        res = self.client.get("/api/violations?q=helmet")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("ok"))

    def test_list_violations_status_filter(self):
        """Test UI status filters: pending, reviewed, resolved."""
        self._login()
        for st in ("pending", "reviewed", "resolved"):
            res = self.client.get(f"/api/violations?status={st}")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("ok"))
            for item in data.get("data", []):
                self.assertEqual(item["ui_status"].lower(), st)

    def test_list_violations_pagination(self):
        """Test server-side pagination with page and page_size."""
        self._login()
        res = self.client.get("/api/violations?page=1&page_size=5")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 5)
        self.assertLessEqual(len(data["data"]), 5)

        if data["total"] > 5:
            res_p2 = self.client.get("/api/violations?page=2&page_size=5")
            self.assertEqual(res_p2.status_code, 200)
            data_p2 = res_p2.get_json()
            self.assertEqual(data_p2["page"], 2)
            if data_p2["data"]:
                # S.No on page 2 must start at 6
                self.assertEqual(data_p2["data"][0]["sno"], 6)

    def test_list_violations_input_validation(self):
        """Test input validation for page and page_size."""
        self._login()
        # Invalid page
        res = self.client.get("/api/violations?page=invalid")
        self.assertEqual(res.status_code, 400)
        # Bad page_size string
        res = self.client.get("/api/violations?page_size=bad")
        self.assertEqual(res.status_code, 400)

    def test_status_update_unauthorized(self):
        """Test unauthenticated PATCH /api/violations/<id>/status is rejected with 401."""
        # Client without session login
        res = self.client.patch("/api/violations/1/status", json={"status": "resolved"})
        # Should be rejected with 401 (or 302 if intercepted by global auth)
        self.assertIn(res.status_code, (401, 302))

    def test_status_update_lifecycle_and_audit_history(self):
        """Test updating status from pending to reviewed and resolved, verifying audit history."""
        self._login()
        # Find an existing violation ID
        v_rows = execute_query("SELECT id FROM violations LIMIT 1", fetch=True)
        if not v_rows:
            self.skipTest("No violations in database to test update.")

        target_id = v_rows[0]["id"]

        # 1. Update to 'reviewed'
        res = self.client.patch(f"/api/violations/{target_id}/status", json={"status": "reviewed", "notes": "Reviewed by QA"})
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data.get("ok"))
        self.assertEqual(json_data["data"]["ui_status"], "Reviewed")

        # 2. Update to 'resolved'
        res2 = self.client.patch(f"/api/violations/{target_id}/status", json={"status": "resolved", "notes": "Resolved by QA"})
        self.assertEqual(res2.status_code, 200)
        json_data2 = res2.get_json()
        self.assertTrue(json_data2.get("ok"))
        self.assertEqual(json_data2["data"]["ui_status"], "Resolved")

        # 3. Verify audit trail in history endpoint
        hist_res = self.client.get(f"/api/violations/{target_id}/history")
        self.assertEqual(hist_res.status_code, 200)
        hist_data = hist_res.get_json()
        self.assertTrue(hist_data.get("ok"))
        self.assertGreaterEqual(len(hist_data["history"]), 2)

    def test_status_update_missing_id(self):
        """Test updating a non-existent violation ID returns 404."""
        self._login()
        res = self.client.patch("/api/violations/9999999/status", json={"status": "resolved"})
        self.assertEqual(res.status_code, 404)

    def test_status_update_invalid_status(self):
        """Test updating with an invalid status returns 400."""
        self._login()
        res = self.client.patch("/api/violations/1/status", json={"status": "invalid_status_xyz"})
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
