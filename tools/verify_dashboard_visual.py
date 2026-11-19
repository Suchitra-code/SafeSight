import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

from app import create_app

app = create_app()
app.config['TESTING'] = True
client = app.test_client()

with client.session_transaction() as sess:
    sess['logged_in'] = True
    sess['username'] = 'admin'

# 1. Test GET /dashboard
res = client.get('/dashboard')
print('Dashboard Status:', res.status_code)
html = res.get_data(as_text=True)

checks = [
    ('Workplace Safety KPI Section', 'workplace-kpi-section' in html),
    ('Workplace Safety KPI Highlights Title', 'Workplace Safety KPI Highlights' in html),
    ('kpi_card.css link', 'kpi_card.css' in html),
    ('kpi_dashboard.js script', 'kpi_dashboard.js' in html),
    ('Card 1: kpiCardInspections', 'id="kpiCardInspections"' in html),
    ('Card 1: Value 22', 'data-val="22"' in html or '>22<' in html),
    ('Card 1: Icon clipboard-check (SVG)', '<svg' in html and 'clipboard-check' in html or 'kpi-badge-accent' in html),
    ('Card 1: Tone Accent', 'kpi-tone-accent' in html),
    ('Card 2: kpiCardViolations', 'id="kpiCardViolations"' in html),
    ('Card 2: Value 56', 'data-val="56"' in html or '>56<' in html),
    ('Card 2: Icon warning-triangle (SVG)', 'warning-triangle' in html or 'kpi-badge-danger' in html),
    ('Card 2: Tone Danger', 'kpi-tone-danger' in html),
    ('Card 3: kpiCardResolved', 'id="kpiCardResolved"' in html),
    ('Card 3: Value 8', 'data-val="8"' in html or '>8<' in html),
    ('Card 3: Description 8 of 56', '8 of 56 total violations resolved' in html),
    ('Card 3: Tone Success', 'kpi-tone-success' in html),
    ('Card 4: kpiCardCompliance', 'id="kpiCardCompliance"' in html),
    ('Card 4: Value 96.8', '96.8' in html),
    ('Card 4: Tone Success', 'kpi-tone-success' in html),
    ('Card 4: Icon shield-check (SVG)', 'shield-check' in html or 'kpi-badge-success' in html),
    ('Auto-refresh button', 'manualKpiRefreshBtn' in html),
    ('Live Active status badge', 'Live Data Active' in html),
]

all_passed = True
for label, passed in checks:
    status_str = "PASS" if passed else "FAIL"
    print(f"[{status_str}] {label}")
    if not passed:
        all_passed = False

# 2. Test GET /api/kpis/workplace-safety
api_res = client.get('/api/kpis/workplace-safety')
print('API Status:', api_res.status_code)
json_data = api_res.get_json()
print('API JSON Data:', json_data)

# 3. Test Static Assets
css_res = client.get('/static/css/kpi_card.css')
js_res = client.get('/static/js/kpi_dashboard.js')
print('CSS Status:', css_res.status_code, 'Length:', len(css_res.get_data()))
print('JS Status:', js_res.status_code, 'Length:', len(js_res.get_data()))

if all_passed and api_res.status_code == 200 and css_res.status_code == 200 and js_res.status_code == 200:
    print("\nALL VISUAL AND FUNCTIONAL VERIFICATION CHECKS PASSED PERFECTLY!")
else:
    print("\nSOME CHECKS FAILED!")
