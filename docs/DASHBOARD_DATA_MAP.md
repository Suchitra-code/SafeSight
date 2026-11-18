# SafeSight AI - Dashboard Data Map & Source Traceability

This document maps every KPI, chart, and widget specified in the Dashboard Redesign prompt to its underlying database table, column, and REST API endpoint, verifying data availability.

---

## 1. Row 1: KPI Metric Cards (6 Cards)

| # | Metric Name | Database Table & Columns | API Endpoint & Key | Status | Trend Chip Logic |
|---|---|---|---|---|---|
| 1 | **Total Workers Detected** | `detections.total_people` (SUM) | `/api/analytics/kpi` -> `total_people` | **AVAILABLE** | Previous-period comparison (or hidden if 1 period) |
| 2 | **Compliant Personnel** | `detections.safe_count` (SUM) | `/api/analytics/kpi` -> `safe_count` | **AVAILABLE** | Up/down % vs prior 7-day period |
| 3 | **Unsafe Personnel** | `detections.unsafe_count` (SUM) | `/api/analytics/kpi` -> `unsafe_count` | **AVAILABLE** | Up/down % vs prior 7-day period |
| 4 | **Safety Compliance Rate** | `(safe_count / total_people) * 100` | `/api/analytics/kpi` -> `compliance_percent` | **AVAILABLE** | Rate trend vs target baseline |
| 5 | **Total PPE Violations** | `COUNT(*) FROM violations` | `/api/analytics/kpi` -> `total_violations` | **AVAILABLE** | Up/down % vs prior period |
| 6 | **Reports Generated** | `COUNT(*)` in `reports/` folder & `documents` (type='report') | `/api/analytics/kpi` -> `reports_count` | **AVAILABLE** | Count of generated executive reports |

---

## 2. Row 2: Visual Telemetry & Recent Activity (3 Columns)

| Widget Name | Database Table & Columns | API Endpoint | Status | UI Behavior & Empty State |
|---|---|---|---|---|
| **Safety Compliance Overview** | Daily aggregates of `detections.safe_count`, `total_people`, and `violations` | `/api/analytics/compliance-trend` | **AVAILABLE** | Line chart comparing Compliance % and Violations count over time with mint and coral palette lines. |
| **Live Detection Result** | `uploads.output_path`, `uploads.filename`, `uploads.camera_name`, `violations` | `/api/analytics/latest-detections` | **AVAILABLE** | Interactive carousel with prev/next arrows showing latest annotated detections with bounding boxes and compliance status. Friendly empty state if no upload. |
| **Recent Violations** | `violations.violation_type`, `violations.severity`, `violations.snapshot_path`, `violations.detected_at`, `violations.location` | `/api/violations?per_page=5` | **AVAILABLE** | List of latest 3-5 violations with snapshots, timestamps, camera locations, and severity pills (High=Red, Med=Orange, Low=Sun). "View All" link to `/events`. |

---

## 3. Row 3: PPE Category & Distribution Analytics (3 Columns)

| Widget Name | Database Table & Columns | API Endpoint | Status | Chart Type & Palette |
|---|---|---|---|---|
| **PPE Detection Summary** | `detections.safe_count`, `unsafe_count` + counts by category | `/api/analytics/ppe-summary` | **AVAILABLE** | Doughnut chart with center text showing Compliance %. Categories: With PPE (Mint), Without PPE (Coral/Red), and real detected categories. |
| **Violation Analysis** | `violations.violation_type`, `COUNT(*)` | `/api/analytics/violations-by-type` | **AVAILABLE** | Bar chart broken down by category (Helmet, Safety Vest, Goggles). |
| **Violation Distribution** | `violations.violation_type` grouped proportions | `/api/analytics/violations-by-type` | **AVAILABLE** | Pie / polar chart displaying percentage share of each infraction category. |

---

## 4. Row 4: Historical & Target Performance (3 Columns)

| Widget Name | Database Table & Columns | API Endpoint | Status | Details & Logic |
|---|---|---|---|---|
| **Daily PPE Events** | `violations.detected_at`, `violation_type` (21-day timeseries) | `/api/analytics/timeseries` | **AVAILABLE** | Area chart showing daily infraction frequencies per PPE type. |
| **Compliance Trends (Target vs Achieved)** | Daily/Weekly compliance rate vs `config.COMPLIANCE_TARGET` | `/api/analytics/compliance-target-trends` | **AVAILABLE** | Grouped bar chart comparing real achieved compliance against target setting (default: 95%). |
| **Monthly Safety Performance** | Aggregated monthly compliance % and violation counts | `/api/analytics/monthly-performance` | **AVAILABLE** | Monthly bar/line comparison. If < 2 months of data exist, renders a friendly "Needs more data" empty state. |

---

## 5. Row 5: System Health & AI Engine Status

| Health Component | Health Check Origin | Health API Endpoint | Display Status Logic |
|---|---|---|---|
| **Database** | MySQL connection or SQLite fallback | `/api/health` -> `database` | Green = Online, Yellow = SQLite Fallback, Red = Offline |
| **YOLOv8 Vision Engine** | `models/best.pt` file check | `/api/health` -> `detector` | Green = Weights Active, Yellow = High-fidelity Demo |
| **Document Index** | FAISS index & chunks count | `/api/health` -> `document_index` | Green = Online with chunk count, Yellow = Offline fallback |
| **Visual Index** | FAISS visual index & indexed count | `/api/health` -> `visual_index` | Green = Online with events count |
| **LLM Provider** | API client check (Gemini / Offline) | `/api/health` -> `llm_provider` | Green = Connected, Yellow = Offline Template Mode |
| **LangGraph Engine** | StateGraph check & checkpointer DB | `/api/health` -> `langgraph` | Green = v1.2.20 Active with SQLite Checkpointer |
| **Design System** | `tools/check_colors.py` scan | `/api/health` -> `theme_colors` | Green = Sunrise Garden (0 violations) |

---

## 6. Row 6: Reports & Quick Action Cards

| Action Card | Target Route / API Endpoint | UI Interaction |
|---|---|---|
| **Download Compliance Report** | `/api/reports/<latest>/download` | Fetches latest executive PDF, shows loading spinner and success toast. |
| **View Violation Report** | `/reports` | Navigates to full Reports & Audits directory. |
| **Generate Safety Summary PDF** | `/api/reports/generate` (POST) | Triggers on-demand ReportLab PDF compilation with toast confirmation. |
| **View All Events** | `/events` | Navigates to real-time CCTV events audit table. |
| **Site Safety Score Gauge** | `/api/analytics/safety-score` | Circular animated canvas gauge rendered in Mint/Sun/Red with compliance status. |
