"""
Integration tests for Workplace Safety KPI API endpoint (/api/kpis/workplace-safety).
"""
import unittest
from unittest.mock import patch
from app import create_app


class TestKpiApi(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"

    def test_get_workplace_safety_kpis_success(self):
        """Test GET /api/kpis/workplace-safety returns 200 and valid schema."""
        res = self.client.get("/api/kpis/workplace-safety")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIsNotNone(json_data)
        self.assertTrue(json_data.get("ok"))
        self.assertIn("data", json_data)

        data = json_data["data"]
        self.assertIn("total_inspections", data)
        self.assertIn("total_violations", data)
        self.assertIn("resolved_violations", data)
        self.assertIn("compliance_percentage", data)
        self.assertIn("compliance_tone", data)
        self.assertIn("generated_at", data)
        self.assertIn("is_demo", data)

        # Confirm data types
        self.assertIsInstance(data["total_inspections"], int)
        self.assertIsInstance(data["total_violations"], int)
        self.assertIsInstance(data["resolved_violations"], int)
        self.assertTrue(
            data["compliance_percentage"] is None or isinstance(data["compliance_percentage"], (int, float))
        )

    def test_get_workplace_safety_kpis_error_handling(self):
        """Test 500 status returned when service reports backend failure."""
        with patch("app.services.kpi_service.get_workplace_safety_kpis") as mock_service:
            mock_service.return_value = {
                "ok": False,
                "error": "Simulated database connection failure"
            }
            res = self.client.get("/api/kpis/workplace-safety")
            self.assertEqual(res.status_code, 500)
            json_data = res.get_json()
            self.assertFalse(json_data.get("ok"))
            self.assertIn("Simulated database connection failure", json_data.get("error", ""))


if __name__ == "__main__":
    unittest.main()
