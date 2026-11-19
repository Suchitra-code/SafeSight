# Workplace Safety KPI Inspection Notes

**Date:** November 2026  
**System:** SafeSight AI (PPE Safety Detection Platform)

---

## 1. Stack & Architectural Analysis
- **Backend Framework:** Python 3.12 with Flask application factory pattern (`app/__init__.py`, `app/routes/`, `app/services/`).
- **Database Engine:** MySQL with transparent SQLite fallback (`database/safesight_fallback.db`), managed via unified DB helper (`app/db.py`) supporting parameterised queries.
- **Frontend Engine:** Jinja2 server-rendered templates (`app/templates/`) integrated with vanilla ES6 JavaScript modules and Chart.js 4.x locally bundled.
- **Theme & Design System:** Strictly enforces "Sunrise Garden" (`app/static/css/theme.css`), prohibiting black and blue (Hue 175°–275° with saturation > 12%, lightness < 18%).
- **Verification Tooling:** `tools/check_colors.py` AST/regex scanner ensures 0 forbidden colours across CSS, JS, and HTML templates.

---

## 2. Real Data Sources for the 4 Workplace Safety KPIs

| KPI Card | Metric Definition | Underlying Table & Column | Real DB Value Found | Tone & Visual Rule |
| :--- | :--- | :--- | :--- | :--- |
| **Total Inspections** | Count of all media inspections processed by the vision pipeline | `uploads` table (`COUNT(*)`) where status != 'failed' | **22** inspections | Accent (`var(--coral)`, `#FF6B4A`) |
| **Total PPE Violations** | Total recorded PPE infractions across all surveillance channels | `violations` table (`COUNT(*)`) across all status types | **56** infractions | Danger (`var(--red)`, `#E53950`) |
| **Resolved Violations** | Infractions actioned, audited, and resolved by safety supervisors | `violations` table (`COUNT(*)`) where `LOWER(status) = 'resolved'` | **8** resolved (8 of 56 total) | Success (`var(--mint)`, `#22B573`) |
| **Compliance Percentage** | Ratio of compliant personnel to total detected personnel | `detections` table: `(SUM(safe_count) / SUM(total_people)) * 100` | **96.8%** (298 safe / 308 workers) | Threshold-based: >=90% Mint, 75–89% Sun, <75% Red |

---

## 3. Plan for Implementation & Reusable Component
1. **Service Layer (`app/services/kpi_service.py`)**:
   - Encapsulates database aggregation queries with parameterised SQL.
   - Handles zero inspections, zero workers (safe fallback instead of NaN), and guards `resolved <= total`.
   - Returns typed dict with timestamps and data integrity verification.

2. **API Endpoint (`GET /api/kpis/workplace-safety`)**:
   - Thin REST route registered in `app/routes/api.py`.
   - Emits standardized JSON: `{ "ok": true, "data": { "total_inspections": 22, "total_violations": 56, "resolved_violations": 8, "compliance_percentage": 96.8, "generated_at": "...", "is_demo": false } }`.

3. **Reusable `KpiCard` Component**:
   - **Template Partial / Macro (`app/templates/components/kpi_card.html`)**: Reusable Jinja macro taking `(title, value, unit, icon, tone, description, trend, state, is_demo, card_id)`.
   - **Styling (`app/static/css/kpi_card.css`)**: Isolated CSS using only Sunrise Garden theme variables (`--coral`, `--mint`, `--red`, `--sun`, `--bg-card`, etc.), 20px border radius, warm tinted shadows, skeleton shimmer, and responsive equal-height flexbox.
   - **Client Script (`app/static/js/kpi_dashboard.js`)**: Auto-refreshes every 60s (pauses when document is hidden), handles manual Refresh, skeleton shimmer on loading, friendly error fallback with a "Retry" button, and count-up number animations (respecting `prefers-reduced-motion`).

4. **Dashboard Integration**:
   - Inserted at the top of `app/templates/dashboard.html` as the dedicated "Workplace Safety KPIs" section without altering or deleting any existing charts, widgets, or health cards.
