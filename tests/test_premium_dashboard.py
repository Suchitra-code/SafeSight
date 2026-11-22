"""
Unit and Integration Tests for Premium Workplace Safety Intelligence Platform (Milestone 5).
Validates filter options, zone risk heatmap, department benchmarks, safety performance scores,
AI insights, forecast projection, inspection scheduling, export, and /dashboard page rendering.
"""
import pytest
import sqlite3
import pathlib
from datetime import datetime

from app import create_app
from app.services import analytics, kpi_service


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "supervisor_test"
    return client


class TestPremiumDashboardServices:
    """Unit tests for analytics calculations and data integrity invariants."""

    def test_filter_options_returns_distinct_real_db_values(self):
        opts = analytics.get_filter_options()
        assert "departments" in opts
        assert "locations" in opts
        assert "types" in opts
        assert "statuses" in opts
        assert len(opts["departments"]) > 0
        assert len(opts["locations"]) > 0
        assert len(opts["types"]) > 0
        # Statuses must cover Pending, Reviewed, Resolved
        status_vals = [s["value"] for s in opts["statuses"]]
        assert "pending" in status_vals
        assert "reviewed" in status_vals
        assert "resolved" in status_vals

    def test_zone_risk_heatmap_calculation(self):
        zones = analytics.get_zone_risk_heatmap()
        assert isinstance(zones, list)
        assert len(zones) > 0
        for z in zones:
            assert "zone" in z
            assert "department" in z
            assert "total_violations" in z
            assert "risk_score" in z
            assert "risk_level" in z
            assert z["risk_level"] in ["Low", "Medium", "High", "Critical"]
            assert 0.0 <= z["risk_score"] <= 100.0

    def test_department_performance_metrics(self):
        depts = analytics.get_department_performance()
        assert isinstance(depts, list)
        assert len(depts) > 0
        for d in depts:
            assert "department" in d
            assert "total_inspections" in d
            assert "total_violations" in d
            assert "resolved_violations" in d
            assert "compliance_rate" in d
            assert d["resolved_violations"] <= d["total_violations"]

    def test_safety_performance_score_formula(self):
        score_data = analytics.get_safety_performance_score()
        assert "score" in score_data
        assert "grade" in score_data
        assert "status" in score_data
        assert "components" in score_data
        assert 0.0 <= score_data["score"] <= 100.0
        # Verify formula: 50% comp + 30% res + 20% audit
        comp = score_data["components"]["compliance_rate"]["value"]
        res = score_data["components"]["resolution_rate"]["value"]
        audit = score_data["components"]["audit_consistency"]["value"]
        expected = round((comp * 0.50) + (res * 0.30) + (audit * 0.20), 1)
        assert abs(score_data["score"] - expected) < 0.15

    def test_ai_safety_insights_structure(self):
        insights = analytics.get_ai_safety_insights()
        assert isinstance(insights, list)
        assert len(insights) >= 3
        for ins in insights:
            assert "title" in ins
            assert "fact" in ins
            assert "category" in ins
            assert "tone" in ins
            assert "action_query" in ins
            assert ins["tone"] in ["peach", "pink", "mint", "orchid", "sun", "coral"]

    def test_predictive_forecast_has_enough_data_or_friendly_fallback(self):
        forecast = analytics.get_predictive_safety_forecast()
        assert "has_enough_data" in forecast
        if forecast["has_enough_data"]:
            assert "predicted_compliance" in forecast
            assert "confidence_interval" in forecast
            assert "note" in forecast
        else:
            assert "message" in forecast


class TestPremiumDashboardAPIs:
    """Integration tests for all newly registered analytics endpoints."""

    def test_filter_options_api(self, auth_client):
        res = auth_client.get("/api/analytics/filter-options")
        assert res.status_code == 200
        data = res.get_json()
        assert "departments" in data
        assert "locations" in data

    def test_zone_risk_heatmap_api_with_department_filter(self, auth_client):
        res = auth_client.get("/api/analytics/zone-risk-heatmap?department=Fabrication")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)

    def test_critical_alerts_api(self, auth_client):
        res = auth_client.get("/api/analytics/critical-alerts")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)

    def test_resolution_metrics_api(self, auth_client):
        res = auth_client.get("/api/analytics/resolution-metrics")
        assert res.status_code == 200
        data = res.get_json()
        assert "resolution_rate" in data
        assert "total_violations" in data

    def test_export_excel_api_csv_download(self, auth_client):
        res = auth_client.get("/api/analytics/export-excel")
        assert res.status_code == 200
        assert "text/csv" in res.content_type
        text = res.data.decode("utf-8")
        assert "SAFESIGHT AI - WORKPLACE SAFETY AUDIT REPORT" in text
        assert "KEY PERFORMANCE INDICATORS" in text

    def test_inspection_schedules_list_api(self, auth_client):
        res = auth_client.get("/api/inspections/schedules")
        assert res.status_code == 200
        data = res.get_json()
        assert data.get("ok") is True
        assert isinstance(data.get("data"), list)

    def test_inspection_schedule_create_requires_auth(self, client):
        # Unauthenticated POST must return 401
        res = client.post("/api/inspections/schedules", json={
            "title": "Unauth Audit",
            "department": "Fabrication",
            "location": "Zone A",
            "scheduled_date": "2026-11-30",
            "assignee": "Anon"
        })
        # App redirects to login (302) or returns 401
        assert res.status_code in [302, 401]

    def test_inspection_schedule_create_and_status_patch(self, auth_client):
        # 1. Create schedule
        create_res = auth_client.post("/api/inspections/schedules", json={
            "title": "Automated Test Inspection",
            "department": "Assembly",
            "location": "Zone B - Assembly Line",
            "scheduled_date": "2026-12-01",
            "assignee": "Alex Test",
            "notes": "Testing schedule API"
        })
        assert create_res.status_code == 201
        assert create_res.get_json().get("ok") is True

        # 2. Verify it appears in list
        list_res = auth_client.get("/api/inspections/schedules")
        schedules = list_res.get_json().get("data", [])
        created = [s for s in schedules if s["title"] == "Automated Test Inspection"]
        assert len(created) > 0
        sched_id = created[0]["id"]

        # 3. Patch status to completed
        patch_res = auth_client.patch(f"/api/inspections/schedules/{sched_id}/status", json={
            "status": "completed"
        })
        assert patch_res.status_code == 200
        assert patch_res.get_json().get("ok") is True

    def test_dashboard_page_renders_with_premium_components(self, auth_client):
        res = auth_client.get("/dashboard")
        assert res.status_code == 200
        html = res.data.decode("utf-8")
        # Check core sections
        assert "hero-welcome-banner" in html
        assert "premium-filter-bar" in html
        assert "workplace-kpi-grid" in html
        assert "kpiCardInspections" in html
        assert "kpiCardViolations" in html
        assert "kpiCardResolved" in html
        assert "kpiCardCompliance" in html
        assert "complianceOverviewChart" in html
        assert "violationsTypeChart" in html
        assert "zoneRiskHeatmapContainer" in html
        assert "deptPerformanceChart" in html
        assert "aiInsightsGrid" in html
        assert "scheduleInspectionModal" in html
        assert "scorePopoverModal" in html
