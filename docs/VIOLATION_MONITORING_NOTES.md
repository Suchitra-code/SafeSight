# SafeSight AI — Violation Monitoring Inspection & Architecture Notes

## 1. System Inspection Summary
- **Framework & Stack:** Python 3.12, Flask, Jinja2 templates, Chart.js / Plotly, MySQL with built-in SQLite automatic fallback (`database/safesight_fallback.db`).
- **Layout & Navigation:**
  - Base template: `app/templates/base.html`
  - Sidebar links: Mission Control (`/command-center`), Home (`/`), Dashboard (`/dashboard`), Upload (`/upload`), Live Monitor (`/live`), Events & Audit (`/events`), Documents, Knowledge Base, Repositories, Reports, AI Assistant, Investigations.
  - New Route: `/violation-monitoring` will be registered in `app/routes/pages.py` and placed directly after `Events & Audit` in `app/templates/base.html` with an active highlighting check (`active_page == 'violation_monitoring'`).
- **Color Palette & Theme Standards:**
  - Strict "Sunrise Garden" theme: **0 black, 0 blue**.
  - Theme variables from `static/css/theme.css`:
    - Coral: `#FF6B4A`, Orange: `#FF9F1C`, Sun: `#FFC93C`, Mint: `#22B573`, Red: `#E53950`, Pink: `#FF4D8D`, Magenta: `#D6247F`, Berry: `#B5179E`.
    - Text: `#4A1D2F` / `#6B3A4D`, Soft backgrounds: `#FFFDF9`, `#FFF8F5`, `#FFFFFF`.
    - Modal backdrop: `rgba(74, 29, 47, 0.35)` (warm translucent plum, strictly no black).
  - Validation tool: `tools/check_colors.py` must report 0 forbidden colors.

## 2. Database Schema & Data Models
- **Table `violations`:**
  - `id`: INTEGER PRIMARY KEY
  - `upload_id`: INTEGER (FK to uploads)
  - `detection_id`: INTEGER (FK to detections)
  - `violation_type`: TEXT (`helmet`, `vest`, `goggles`, `other`)
  - `severity`: TEXT (`HIGH`, `MEDIUM`, `LOW`)
  - `confidence`: REAL (0.0 to 1.0)
  - `snapshot_path`: TEXT (image filename)
  - `camera_name`: TEXT (`Cam 01 - Zone A`, etc.)
  - `location`: TEXT (`Zone A - Fabrication`, `Main Facility`, etc.)
  - `status`: TEXT (`detected`, `pending review`, `confirmed`, `dismissed`, `resolved`)
  - `reviewed_by`: TEXT
  - `notes`: TEXT
  - `detected_at`: TIMESTAMP
  - `updated_at`: TIMESTAMP
- **Additive Migration:**
  - Safe migration in `app/db.py` to ensure `department` column exists (`ALTER TABLE violations ADD COLUMN department TEXT DEFAULT NULL;` if not already present).
  - Safe creation of `violation_status_history` table for immutable audit logging:
    ```sql
    CREATE TABLE IF NOT EXISTS violation_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        violation_id INTEGER NOT NULL,
        old_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        changed_by TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

## 3. Status Mapping & Business Logic
The 5 database statuses are mapped cleanly to 3 user-facing statuses without losing granularity:

| UI Status | Color / Tone | DB Statuses Covered | DB Status Written on Update | Notes |
|---|---|---|---|---|
| **Pending** | Orange (`var(--orange)`) | `detected`, `pending review` | `pending review` | Initial or flagged events awaiting verification |
| **Reviewed** | Berry / Magenta (`var(--berry)`) | `confirmed`, `dismissed` | `confirmed` (or `dismissed` if specified) | Audited by safety officer; tooltip shows "Dismissed" if dismissed |
| **Resolved** | Mint Green (`var(--mint)`) | `resolved` | `resolved` | Corrective action taken and closed |

Summary metric rule:
`Total Violations == Pending + Reviewed + Resolved` (Every database record is accounted for).

## 4. Violation Type Mapping
Raw codes mapped to clean, professional names with inline SVG chips:
- `helmet`, `no helmet`, `no_hardhat` $\rightarrow$ **Missing Helmet**
- `vest`, `no vest`, `no_safety_vest` $\rightarrow$ **Missing Safety Vest**
- `equipment`, `several ppe items missing`, `no_equipment` $\rightarrow$ **No Safety Equipment**
- `goggles`, `gloves`, `shoes`, `other`, etc. $\rightarrow$ **Other Safety Violation**

## 5. Reusable Components & Endpoints to Reuse
- Reusable `render_kpi_card` macro from `app/templates/components/kpi_card.html` for the 4 summary cards.
- Enhanced `GET /api/violations` supporting:
  - `q`: search query against violation type, location, camera, notes
  - `type`: violation type filter (mapped or raw)
  - `status`: UI status (`pending`, `reviewed`, `resolved`) or raw status
  - `date`: exact date (`YYYY-MM-DD`)
  - `from`, `to`: date range
  - `page`, `page_size`: server-side pagination
  - Response shape: `{ "ok": true, "data": [...], "items": [...], "total": N, "page": P, "page_size": S, "counts": { "total": T, "pending": P, "reviewed": R, "resolved": S } }`
- Enhanced `PATCH /api/violations/<id>/status` with:
  - Body: `{ "status": "pending|reviewed|resolved|confirmed|dismissed", "notes": "..." }`
  - Authentication check enforcing logged-in user on server
  - Automatic entry written to `violation_status_history`
- Safe image serving: `GET /api/violations/<id>/snapshot` or `/outputs/<filename>` with fallback to inline SVG placeholder.

## 6. Implementation Plan
1. Helper module `app/services/violation_mapper.py`: pure mapping functions for status, type, date/time split, and S.No calculation.
2. DB Migration in `app/db.py`: `violation_status_history` table and safe check for `department`.
3. Service functions in `app/services/violation_service.py` to handle the mapped querying, counts aggregation, and audit logging.
4. API endpoints in `app/routes/api.py`: `GET /api/violations` (with `counts` and `data`), `PATCH /api/violations/<id>/status` with auth and audit.
5. Page route in `app/routes/pages.py`: `GET /violation-monitoring`.
6. Frontend Template `app/templates/violation_monitoring.html`:
   - Summary KPI cards
   - Filter bar: search, type dropdown, status dropdown, date picker, range picker, clear filters button, active chips
   - Accessible table with sticky header and peach zebra rows
   - Mobile responsive card stack view
   - Server-side pagination controls
   - Image Preview modal with Esc/backdrop close, focus trapping, and Prev/Next cycling
   - Toast notification system for instant updates
7. Dedicated CSS `app/static/css/violation_monitoring.css` (Sunrise Garden variables only, 0 black, 0 blue).
8. Client-side controller `app/static/js/violation_monitoring.js`.
9. Unit and integration tests in `tests/test_violation_mapper.py` and `tests/test_violation_monitoring_api.py`.
10. Full verification with `tools/check_colors.py` and `scripts/smoke_test.py`.
