import sys, os, pathlib
ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import create_app

app = create_app()
app.config["TESTING"] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess["logged_in"] = True
    sess["user"] = "admin"

endpoints = [
    "/api/analytics/filter-options",
    "/api/kpis/workplace-safety",
    "/api/analytics/zone-risk-heatmap",
    "/api/analytics/department-performance",
    "/api/analytics/critical-alerts",
    "/api/analytics/resolution-metrics",
    "/api/analytics/safety-performance-score",
    "/api/analytics/ai-insights",
    "/api/analytics/forecast",
    "/api/inspections/schedules"
]

for ep in endpoints:
    res = client.get(ep)
    print(f"{ep:<40} -> status {res.status_code}")
    if res.status_code != 200:
        print("  Error:", res.data.decode()[:200])
    else:
        try:
            d = res.get_json()
            keys = list(d.keys()) if isinstance(d, dict) else f"list({len(d)})"
            print(f"  OK: {keys}")
        except Exception as e:
            print("  JSON parse err:", e)
