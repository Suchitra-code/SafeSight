# SafeSight AI — Current State Audit (Pre-Milestone 5)

## Project Structure
```
safesight-ai/
├── app/
│   ├── __init__.py              # Flask factory, blueprint registration
│   ├── db.py                    # Database layer (MySQL + SQLite fallback)
│   ├── agents/                  # M3 LangGraph investigation
│   │   ├── investigation_graph.py, state.py, tools.py, risk.py, runner.py
│   ├── copilot/                 # M4 LangGraph copilot
│   │   ├── graph.py, state.py, schemas.py, events.py, run_store.py
│   │   ├── validators.py, offline_templates.py, suggestions.py
│   │   └── nodes/ (query_analysis, visual_retrieval, document_retrieval,
│   │               evidence_check, answer_generation, answer_validation,
│   │               support_nodes, final_response)
│   ├── llm/                     # LLM provider abstraction
│   │   ├── provider.py, fake_llm.py, prompts.py
│   ├── rag/                     # RAG pipeline
│   │   ├── rag_pipeline.py, retriever.py, context_builder.py
│   │   ├── visual_indexer.py, visual_linker.py, guardrails.py
│   ├── routes/                  # Flask blueprints
│   │   ├── pages.py, api.py, stream.py, auth.py
│   │   ├── documents.py, knowledge.py, health.py
│   │   ├── assistant.py, investigations.py
│   │   ├── copilot.py, command_center.py
│   ├── services/                # Business logic
│   │   ├── detector.py, violation_service.py, analytics.py
│   │   ├── embedder.py, search_service.py, qa_service.py
│   │   ├── doc_pipeline.py, doc_loader.py, doc_classifier.py
│   │   ├── chunker.py, ocr_service.py, text_cleaner.py
│   │   ├── manual_extractor.py, inspection_extractor.py
│   │   ├── chat_service.py, incident_report_pdf.py
│   │   └── command_center_service.py
│   ├── static/
│   │   ├── css/ (style.css 1463 lines, command_center.css)
│   │   ├── js/ (dashboard.js, events.js, upload.js, live.js, documents.js, knowledge.js)
│   │   ├── js/cc/ (18 modules: main, store, api, copilot, pipeline_viz, etc.)
│   │   ├── vendor/ (chart.umd.min.js)
│   │   └── data/ (site_map.json)
│   └── templates/ (20 HTML files)
├── config.py
├── run.py
├── database/ (schema.sql, schema_milestone2-4.sql, seed scripts)
├── scripts/ (check_langgraph.py, smoke_test.py, eval_copilot.py)
├── tests/ (20 test files, 63 tests total)
├── docs/ (ARCHITECTURE.md, DEMO_SCRIPT.md, MILESTONE4_TRACEABILITY.md)
└── requirements.txt
```

## All Flask Routes (78 total)
### Pages (16)
/, /dashboard, /upload, /live, /events, /reports, /documents, /documents/<id>,
/documents/upload, /knowledge, /repositories, /assistant, /investigations,
/investigations/<run_id>, /command-center, /result/<upload_id>

### Auth (3)
/login, /register, /logout

### APIs — Analytics (9)
/api/analytics/kpi, /safety-score, /violations-by-type, /timeseries,
/heatmap, /compliance-trend, /violations-by-camera, /latest-violation

### APIs — Core (12)
/api/upload, /api/violations, /api/violations/<id>, /api/violations/<id>/snapshot,
/api/violations/<id>/status, /api/violations/<id>/explain, /api/export/violations-csv,
/api/results/<id>, /api/progress/<id>, /api/reports, /api/reports/generate,
/api/reports/<path>/download, /api/seed-demo

### APIs — Documents (10)
/api/documents, /api/documents/upload, /api/documents/<id>, /api/documents/<id>/file,
/api/documents/<id>/progress, /api/documents/<id>/reprocess, /api/documents/<id>/fields/<fid>,
/api/documents/<id>/findings/<fid>, /api/documents/export, /api/seed-documents

### APIs — Knowledge (4)
/api/knowledge/search, /api/knowledge/ask, /api/knowledge/stats, /api/knowledge/rebuild

### APIs — M3 (5)
/api/assistant/ask, /api/assistant/history/<sid>, /api/assistant/feedback/<mid>,
/api/investigations/, /api/investigations/start/<id>

### APIs — M3 Investigation (3)
/api/investigations/<run_id>, /api/investigations/<run_id>/approve,
/api/investigations/<run_id>/reject, /api/investigations/<run_id>/pdf

### APIs — M4 Copilot (7)
/api/copilot/ask, /api/copilot/stream/<run_id>, /api/copilot/runs/<run_id>,
/api/copilot/history, /api/copilot/runs/<run_id>/events, /api/copilot/graph,
/api/copilot/suggestions

### APIs — M4 Command Center (5)
/api/command-center/kpis, /heatmap, /trends, /feed, /zones

### System (2)
/api/health, /api/repositories

## All Templates (20)
base.html, landing.html, dashboard.html, upload.html, result.html, live.html,
events.html, reports.html, documents.html, document_detail.html, document_upload.html,
knowledge.html, repositories.html, assistant.html, investigations.html,
investigation_detail.html, command_center.html, login.html, login_base.html, register.html

## Database Tables
### M1: detections, violations, uploads
### M2: documents, document_chunks, manual_rules, inspection_findings, report_findings, repositories
### M3: visual_chunks, assistant_messages
### M4: copilot_runs, copilot_events, site_zones

## LangGraph Graphs
1. **Investigation Graph** (M3): `app/agents/investigation_graph.py` — 7 nodes
2. **Copilot Graph** (M4): `app/copilot/graph.py` — 13 nodes with conditional routing

## Libraries (key)
Flask, langgraph==1.2.20, pydantic, opencv-python-headless, ultralytics (YOLO),
matplotlib, reportlab, numpy, pandas, faiss-cpu (optional), sentence-transformers (optional)

## Current Theme
- Light/dark toggle (navy + orange)
- CSS variables in style.css `:root`
- Google Fonts CDN (Inter)
- Chart.js, Plotly.js, Mermaid.js from CDN
- Many hardcoded navy/blue colors throughout
