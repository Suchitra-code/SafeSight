"""
Comprehensive Smoke Test for SafeSight AI - Milestone 1, 2, and 3.
Exercises all UI pages and REST APIs, executes an end-to-end investigation run,
and displays a structured PASS/FAIL verification table.
"""
import sys
import os
import pathlib
import json
import logging

# Ensure project root is in sys.path
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app
from app.db import execute_query

# Suppress debug logs for clean output
logging.basicConfig(level=logging.ERROR)


def run_smoke_test():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # Authenticate test session
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user"] = "admin"

    results = []

    # 1. UI Pages
    pages = [
        ("/command-center", "Mission Control Center (M4)"),
        ("/", "Landing Page (M1)"),
        ("/dashboard", "BI Analytics Dashboard (M1)"),
        ("/upload", "Upload & Media Page (M1)"),
        ("/live", "Live Multi-Camera Monitor (M1)"),
        ("/events", "Violation Event Audit (M1)"),
        ("/reports", "Compliance Reports (M1)"),
        ("/documents", "Documents Library (M2)"),
        ("/knowledge", "Searchable Knowledge Base (M2)"),
        ("/repositories", "Knowledge Repositories (M2)"),
        ("/assistant", "AI Safety Assistant RAG (M3)"),
        ("/investigations", "Incident Investigations (M3)"),
    ]

    for url, desc in pages:
        try:
            res = client.get(url)
            status = "PASS" if res.status_code == 200 else f"FAIL ({res.status_code})"
            results.append((desc, url, "GET", status))
        except Exception as e:
            results.append((desc, url, "GET", f"ERROR: {e}"))

    # 2. JSON APIs
    apis = [
        ("/api/health", "System Health Check (M3)"),
        ("/api/analytics/kpi", "Top KPI Metrics (M1)"),
        ("/api/analytics/safety-score", "Site Safety Score (M1)"),
        ("/api/analytics/violations-by-type", "Violations by Type (M1)"),
        ("/api/analytics/timeseries", "Timeseries Data (M1)"),
        ("/api/analytics/heatmap", "Hourly Heatmap Matrix (M1)"),
        ("/api/violations", "Violations Audit API (M1)"),
        ("/api/documents", "Document Management API (M2)"),
        ("/api/repositories", "Repositories API (M2)"),
        ("/api/investigations/", "Investigation Registry API (M3)"),
        ("/api/command-center/kpis", "Mission Control KPIs (M4)"),
        ("/api/command-center/heatmap", "Hourly Violations Matrix (M4)"),
        ("/api/command-center/trends", "14-Day Compliance Trends (M4)"),
        ("/api/command-center/feed", "Live Events Feed (M4)"),
        ("/api/command-center/zones", "Site Map Zones Status (M4)"),
        ("/api/copilot/graph", "Copilot LangGraph Pipeline (M4)"),
        ("/api/copilot/suggestions", "Dynamic Copilot Prompts (M4)"),
        ("/api/copilot/history", "Copilot Runs History (M4)"),
    ]

    for url, desc in apis:
        try:
            res = client.get(url)
            is_json = False
            try:
                data = res.get_json()
                is_json = data is not None
            except Exception:
                is_json = False

            if res.status_code == 200 and is_json:
                status = "PASS"
            else:
                status = f"FAIL (HTTP {res.status_code}, json={is_json})"
            results.append((desc, url, "GET", status))
        except Exception as e:
            results.append((desc, url, "GET", f"ERROR: {e}"))

    # 3. Interactive Milestone 3 Q&A POST
    try:
        q_res = client.post("/api/assistant/ask", json={
            "question": "What PPE is required for welding?",
            "session_id": "smoke_test_session"
        })
        q_data = q_res.get_json()
        if q_res.status_code == 200 and q_data and "answer" in q_data:
            results.append(("RAG Q&A Synthesis with Citations", "/api/assistant/ask", "POST", "PASS"))
        else:
            results.append(("RAG Q&A Synthesis with Citations", "/api/assistant/ask", "POST", f"FAIL ({q_res.status_code})"))
    except Exception as e:
        results.append(("RAG Q&A Synthesis with Citations", "/api/assistant/ask", "POST", f"ERROR: {e}"))

    # 3b. Interactive Milestone 4 SafeSight Copilot POST
    try:
        copilot_res = client.post("/api/copilot/ask", json={
            "question": "What are the rules for safety vests in Zone A?",
            "session_id": "smoke_test_copilot"
        })
        c_data = copilot_res.get_json()
        if copilot_res.status_code == 202 and c_data and c_data.get("success"):
            results.append(("LangGraph Copilot Execution (M4)", "/api/copilot/ask", "POST", "PASS"))
        else:
            results.append(("LangGraph Copilot Execution (M4)", "/api/copilot/ask", "POST", f"FAIL ({copilot_res.status_code})"))
    except Exception as e:
        results.append(("LangGraph Copilot Execution (M4)", "/api/copilot/ask", "POST", f"ERROR: {e}"))

    # 4. End-to-end Investigation Workflow
    try:
        v_rows = execute_query("SELECT id FROM violations LIMIT 1", fetch=True)
        if v_rows:
            v_id = v_rows[0]["id"]
            start_res = client.post(f"/api/investigations/start/{v_id}")
            start_data = start_res.get_json()
            if start_res.status_code == 200 and start_data and "run_id" in start_data:
                run_id = start_data["run_id"]
                # Test supervisor approve
                appr_res = client.post(f"/api/investigations/{run_id}/approve", json={"notes": "Smoke test approve"})
                appr_data = appr_res.get_json()
                if appr_res.status_code == 200 and appr_data.get("status") == "completed":
                    results.append(("End-to-End Investigation Workflow", f"/api/investigations/{run_id}/approve", "POST", "PASS"))
                else:
                    results.append(("End-to-End Investigation Workflow", f"/api/investigations/{run_id}/approve", "POST", "FAIL (Approval failed)"))
            else:
                results.append(("End-to-End Investigation Workflow", f"/api/investigations/start/{v_id}", "POST", "FAIL (Start failed)"))
        else:
            results.append(("End-to-End Investigation Workflow", "/api/investigations/start", "POST", "SKIP (No violations)"))
    except Exception as e:
        results.append(("End-to-End Investigation Workflow", "/api/investigations/start", "POST", f"ERROR: {e}"))

    # Print Formatted Verification Table
    print("\n" + "=" * 80)
    print("                    SAFESIGHT AI - VERIFICATION RESULTS TABLE")
    print("=" * 80)
    print(f"{'Component / Feature':<36} | {'Method':<6} | {'Status':<10} | {'Endpoint'}")
    print("-" * 80)
    all_pass = True
    for desc, url, method, status in results:
        pass_indicator = "[PASS]" if "PASS" in status else f"[{status}]"
        if "PASS" not in status:
            all_pass = False
        print(f"{desc:<36} | {method:<6} | {pass_indicator:<10} | {url}")

    print("=" * 80)
    if all_pass:
        print("ALL PAGES, REST APIS, AND AGENT WORKFLOWS PASSED VERIFICATION!\n")
    else:
        print("SOME CHECKS FAILED. PLEASE REVIEW LOGS ABOVE.\n")
    return all_pass


if __name__ == "__main__":
    success = run_smoke_test()
    sys.exit(0 if success else 1)
