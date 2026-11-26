# Core Safety Indicators Audit (`docs/INDICATORS_AUDIT.md`)

## 1. Existing Dashboard State
- **Primary KPI Section**: `.workplace-kpi-grid` in `app/templates/dashboard.html` using `render_kpi_card` macro (`app/templates/components/kpi_card.html`), styled by `app/static/css/kpi_card.css` + `app/static/css/theme.css` + `app/static/css/vivid.css`, and hydrated via `/api/kpis/workplace-safety` (`app/routes/api.py` -> `app/services/kpi_service.py`).
- **Existing 4 Core Indicators**:
  1. **Total Inspections** (`kpiCardInspections`, tone `peach`): `22` — `SELECT COUNT(*) FROM uploads WHERE status != 'failed'`
  2. **Total PPE Violations** (`kpiCardViolations`, tone `pink`): `68` — `SELECT COUNT(*) FROM violations`
  3. **Resolved Violations** (`kpiCardResolved`, tone `mint`): `9` — `SELECT COUNT(*) FROM violations WHERE LOWER(status) = 'resolved'`
  4. **Compliance Percentage** (`kpiCardCompliance`, tone `orchid`): `95.1%` — `round((safe_count / total_people) * 100.0, 1)` from `detections`
- **Note on Existing Hardcoded 5th Card**: `.workplace-kpi-grid` currently contains a static hardcoded 5th card `kpiCardCorrective` ("Corrective Actions", `"31/33"`). Replacing it with the 4 real-data indicator cards produces the clean 4 columns × 2 rows (8 cards) grid.
- **Note on Existing Duplication in Row 2 (`.kpi-grid-6`)**: `.kpi-grid-6` (`dashboard.html` line 319) already contains a "Reports Generated" card (`kpiReports`, value `60`, from `analytics.get_kpi_summary()["reports_count"]`). Per requirements, `.kpi-grid-6` is left untouched, and the new "Reports Generated" card reuses the exact same calculation so both always agree.

## 2. The 4 New Indicators (Additive Fields on `/api/kpis/workplace-safety`)

| # | Indicator | Card ID | Tone | Source (Table / Module) | Exact Definition | Scope | Baseline |
|---|---|---|---|---|---|---|---|
| 5 | **Open Incidents** | `kpiCardOpenIncidents` | `coral` | `investigation_runs` (`status` column) | `SELECT COUNT(*) FROM investigation_runs WHERE LOWER(status) NOT IN ('completed', 'dismissed', 'resolved', 'closed', 'failed')` | Current state ("as of now") | `1` |
| 6 | **Reports Generated** | `kpiCardReportsGenerated` | `sun` | `config.REPORT_FOLDER` (`*.pdf`), matching `analytics.get_kpi_summary()["reports_count"]` | Count of `.pdf` files in `config.REPORT_FOLDER` (filtered by file mtime when `date_from`/`date_to` are provided) | Follows dashboard period filters | `60` |
| 7 | **Active Safety Alerts** | `kpiCardActiveAlerts` | `red` | `analytics.get_critical_alerts()` (`violations` high/critical unreviewed + repeat hotspots) | `len(analytics.get_critical_alerts())` | Current state ("as of now") | `7` |
| 8 | **Pending Reviews** | `kpiCardPendingReviews` | `lime` | `violations` (`status` column) | `SELECT COUNT(*) FROM violations WHERE LOWER(status) IN ('detected', 'pending review')` (canonical Pending definition in `violation_mapper.py`) | Current state ("as of now") | `38` |

## 3. Distinctness & Unavailable-State Guarantees
- **Distinctness**: `Open Incidents` (1) measures open agentic incident investigation runs (`investigation_runs`), whereas `Pending Reviews` (38) measures individual PPE violation detections awaiting human supervisor sign-off (`violations` in `detected` or `pending review`). Neither overlaps with `Active Safety Alerts` (7 rule-based smart alerts) or `Reports Generated` (60 PDF dossiers).
- **Unavailable vs True Zero**: Each new metric returns `None` (never `0`) if its underlying table/directory/query fails or is missing. The UI renders `kpi-state-unavailable` ("No data source yet" / `—` + Retry) for that specific card only, while the other 7 cards continue working normally.
- **API Contract**: `/api/kpis/workplace-safety` returns additive fields inside `data`: `open_incidents`, `reports_generated`, `active_safety_alerts`, `pending_reviews` (each integer or `null` when unavailable), plus `indicator_errors` dict (optional metadata for per-card error/unavailable state). Existing fields (`total_inspections`, `total_violations`, `resolved_violations`, `compliance_percentage`, `compliance_tone`, `generated_at`, `is_demo`, `warning`) remain 100% unchanged.
