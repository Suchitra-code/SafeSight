"""
Unit tests for SafeSight AI Workplace Safety KPI Service.
Tests pure computation logic, edge cases (zero workers, resolved > total),
and real database integration.
"""
import unittest
from app.services.kpi_service import compute_kpi_metrics, get_workplace_safety_kpis


class TestKpiService(unittest.TestCase):
    def test_compute_kpi_metrics_normal(self):
        """Test normal values calculation."""
        res = compute_kpi_metrics(
            inspections_count=22,
            total_violations=56,
            resolved_violations=8,
            total_people=308,
            safe_count=298,
            is_demo=False
        )
        self.assertEqual(res["total_inspections"], 22)
        self.assertEqual(res["total_violations"], 56)
        self.assertEqual(res["resolved_violations"], 8)
        self.assertEqual(res["compliance_percentage"], 96.8)
        self.assertEqual(res["compliance_tone"], "success")
        self.assertFalse(res["is_demo"])
        self.assertIsNone(res["warning"])

    def test_compute_kpi_metrics_zero_workers(self):
        """Test edge case: zero workers and zero violations (no NaN or division by zero)."""
        res = compute_kpi_metrics(
            inspections_count=0,
            total_violations=0,
            resolved_violations=0,
            total_people=0,
            safe_count=0
        )
        self.assertEqual(res["total_inspections"], 0)
        self.assertEqual(res["total_violations"], 0)
        self.assertEqual(res["resolved_violations"], 0)
        self.assertIsNone(res["compliance_percentage"])
        self.assertEqual(res["compliance_tone"], "empty")

    def test_compute_kpi_metrics_resolved_exceeds_total(self):
        """Test data inconsistency: resolved violations capped at total violations with warning."""
        res = compute_kpi_metrics(
            inspections_count=10,
            total_violations=5,
            resolved_violations=12,
            total_people=100,
            safe_count=95
        )
        self.assertEqual(res["total_violations"], 5)
        self.assertEqual(res["resolved_violations"], 5)
        self.assertIsNotNone(res["warning"])
        self.assertIn("exceeds total", res["warning"])

    def test_compute_kpi_metrics_compliance_tones(self):
        """Test compliance percentage tone thresholds."""
        # >= 90% -> success
        res_high = compute_kpi_metrics(5, 2, 1, 100, 92)
        self.assertEqual(res_high["compliance_tone"], "success")

        # 75% to 89.9% -> warning
        res_mid = compute_kpi_metrics(5, 10, 5, 100, 80)
        self.assertEqual(res_mid["compliance_tone"], "warning")

        # < 75% -> danger
        res_low = compute_kpi_metrics(5, 20, 5, 100, 60)
        self.assertEqual(res_low["compliance_tone"], "danger")

    def test_get_workplace_safety_kpis_integration(self):
        """Test real database query integration."""
        result = get_workplace_safety_kpis()
        self.assertTrue(result.get("ok"))
        data = result.get("data", {})
        self.assertIn("total_inspections", data)
        self.assertIn("total_violations", data)
        self.assertIn("resolved_violations", data)
        self.assertIn("compliance_percentage", data)
        self.assertIn("generated_at", data)
        # Verify values are non-negative integers / float
        self.assertGreaterEqual(data["total_inspections"], 0)
        self.assertGreaterEqual(data["total_violations"], 0)
        self.assertGreaterEqual(data["resolved_violations"], 0)


if __name__ == "__main__":
    unittest.main()
