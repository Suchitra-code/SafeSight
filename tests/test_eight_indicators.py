"""
Unit and Integration Tests for the 8 Core Safety Indicators on SafeSight AI Dashboard.
Verifies:
1. Existing 4 indicators match baseline values exactly.
2. 4 new indicators match direct SQL / source counts.
3. Empty data returns true 0; missing/failed source returns None (unavailable), never fake 0.
4. Simulated failure of one indicator leaves the other 7 working.
5. API endpoint auth, success shape, and error handling.
6. Dashboard HTML renders all 8 cards in order and preserves Row 2 kpiReports.
"""
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import config
from app import create_app
from app.services.cache import clear_analytics_cache
from app.services.kpi_service import (
    compute_kpi_metrics,
    get_workplace_safety_kpis,
    _get_open_incidents_count,
    _get_reports_generated_count,
    _get_active_safety_alerts_count,
    _get_pending_reviews_count,
)


class TestEightCoreIndicators(unittest.TestCase):
    def setUp(self):
        clear_analytics_cache()
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _login(self):
        with self.client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user"] = "admin"

    def test_compute_kpi_metrics_with_8_fields(self):
        res = compute_kpi_metrics(
            inspections_count=22,
            total_violations=68,
            resolved_violations=9,
            total_people=308,
            safe_count=293,
            open_incidents=1,
            reports_generated=60,
            active_safety_alerts=7,
            pending_reviews=38,
        )
        self.assertEqual(res["open_incidents"], 1)
        self.assertEqual(res["reports_generated"], 60)
        self.assertEqual(res["active_safety_alerts"], 7)
        self.assertEqual(res["pending_reviews"], 38)
        self.assertEqual(res["indicator_errors"], {})

    def test_compute_kpi_metrics_true_zero_vs_unavailable(self):
        res_zero = compute_kpi_metrics(0, 0, 0, 0, 0, open_incidents=0, reports_generated=0, active_safety_alerts=0, pending_reviews=0)
        self.assertEqual(res_zero["open_incidents"], 0)
        self.assertEqual(res_zero["reports_generated"], 0)
        self.assertEqual(res_zero["active_safety_alerts"], 0)
        self.assertEqual(res_zero["pending_reviews"], 0)

        res_unavail = compute_kpi_metrics(0, 0, 0, 0, 0)
        self.assertIsNone(res_unavail["open_incidents"])
        self.assertIsNone(res_unavail["reports_generated"])
        self.assertIsNone(res_unavail["active_safety_alerts"])
        self.assertIsNone(res_unavail["pending_reviews"])

    def test_new_indicators_match_direct_source_counts(self):
        conn = sqlite3.connect(os.path.join(config.BASE_DIR, "database", "safesight_fallback.db"))
        sql_open = conn.execute(
            "SELECT COUNT(*) FROM investigation_runs WHERE LOWER(COALESCE(status, '')) NOT IN ('completed', 'dismissed', 'resolved', 'closed', 'failed')"
        ).fetchone()[0]
        sql_pending = conn.execute(
            "SELECT COUNT(*) FROM violations WHERE LOWER(COALESCE(status, 'detected')) IN ('detected', 'pending review')"
        ).fetchone()[0]
        conn.close()

        expected_reports = len([f for f in os.listdir(config.REPORT_FOLDER) if f.lower().endswith(".pdf")])

        oi, err1 = _get_open_incidents_count()
        rg, err2 = _get_reports_generated_count()
        asa, err3 = _get_active_safety_alerts_count()
        pr, err4 = _get_pending_reviews_count()

        self.assertIsNone(err1)
        self.assertIsNone(err2)
        self.assertIsNone(err3)
        self.assertIsNone(err4)
        self.assertEqual(oi, sql_open)
        self.assertEqual(rg, expected_reports)
        self.assertGreaterEqual(asa, 0)
        self.assertEqual(pr, sql_pending)
        # Distinctness check
        self.assertNotEqual(oi, pr)

    def test_empty_reports_folder_returns_true_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(config, "REPORT_FOLDER", tmpdir):
                cnt, err = _get_reports_generated_count()
                self.assertIsNone(err)
                self.assertEqual(cnt, 0)

    def test_missing_reports_folder_returns_unavailable(self):
        with patch.object(config, "REPORT_FOLDER", "/nonexistent/safesight/reports_dir_12345"):
            cnt, err = _get_reports_generated_count()
            self.assertIsNone(cnt)
            self.assertIsNotNone(err)

    def test_missing_table_returns_unavailable_without_breaking_others(self):
        with patch("app.services.kpi_service._get_open_incidents_count", return_value=(None, "no such table: investigation_runs")):
            res = get_workplace_safety_kpis()
            self.assertTrue(res["ok"])
            d = res["data"]
            self.assertIsNone(d["open_incidents"])
            self.assertIn("open_incidents", d["indicator_errors"])
            # Other 7 indicators continue working
            self.assertEqual(d["total_inspections"], 22)
            self.assertEqual(d["total_violations"], 68)
            self.assertEqual(d["resolved_violations"], 9)
            self.assertEqual(d["compliance_percentage"], 95.1)
            self.assertIsNotNone(d["reports_generated"])
            self.assertIsNotNone(d["active_safety_alerts"])
            self.assertIsNotNone(d["pending_reviews"])

    def test_api_requires_auth(self):
        res = self.client.get("/api/kpis/workplace-safety")
        self.assertIn(res.status_code, (302, 401))

    def test_api_success_shape_and_baseline_preservation(self):
        self._login()
        res = self.client.get("/api/kpis/workplace-safety")
        self.assertEqual(res.status_code, 200)
        payload = res.get_json()
        self.assertTrue(payload["ok"])
        d = payload["data"]

        # Baseline 4 exact match
        self.assertEqual(d["total_inspections"], 22)
        self.assertEqual(d["total_violations"], 68)
        self.assertEqual(d["resolved_violations"], 9)
        self.assertEqual(d["compliance_percentage"], 95.1)

        # Extended 4 present and valid
        for key in ("open_incidents", "reports_generated", "active_safety_alerts", "pending_reviews"):
            self.assertIn(key, d)
            self.assertIsInstance(d[key], int)

    def test_dashboard_renders_all_8_cards_in_order(self):
        self._login()
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        expected_ids = [
            "kpiCardInspections",
            "kpiCardViolations",
            "kpiCardResolved",
            "kpiCardCompliance",
            "kpiCardOpenIncidents",
            "kpiCardReportsGenerated",
            "kpiCardActiveAlerts",
            "kpiCardPendingReviews",
        ]
        positions = [html.index(cid) for cid in expected_ids]
        self.assertEqual(positions, sorted(positions))
        # Row 2 duplicate Reports Generated preserved
        self.assertIn('id="kpiReports"', html)

    def test_dashboard_unavailable_card_isolated(self):
        self._login()
        with patch("app.services.kpi_service._get_open_incidents_count", return_value=(None, "source offline")):
            clear_analytics_cache()
            res = self.client.get("/dashboard")
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)
            self.assertIn('kpi-state-unavailable" id="kpiCardOpenIncidents"', html)
            self.assertIn('kpi-state-ready" id="kpiCardPendingReviews"', html)


if __name__ == "__main__":
    unittest.main()
