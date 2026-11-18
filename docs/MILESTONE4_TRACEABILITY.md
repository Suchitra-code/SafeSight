# SafeSight AI - Milestone 4 Traceability Matrix

This document tracks all 10 Mentor Requirements for Milestone 4 (SafeSight Copilot & Mission Control), their exact implementation files, functions/classes, UI display points, and automated test coverage.

| # | Mentor Requirement | Built As | Visible in the UI | Tests & Verification |
|---|-------------------|----------|-------------------|----------------------|
| **1** | **Install and configure LangGraph** | Pinned `langgraph>=1.2.20` in requirements, `scripts/check_langgraph.py`, `/api/health` integration | "Powered by LangGraph vX" badge in Mission Control header + System Health card | `scripts/check_langgraph.py`, `tests/test_copilot_api.py::test_health_check` |
| **2** | **Create a workflow using nodes and edges** | `app/copilot/graph.py` (`build_graph()`, `StateGraph(CopilotState)`) | Live Pipeline SVG graph with real-time active node glow | `tests/test_graph_routes.py::test_build_graph_structure` |
| **3** | **Query analysis node** | `app/copilot/nodes/query_analysis.py` (`query_analysis`), intent extraction & entity parsing | Step 1 of live pipeline viz, shows intent & extracted filters | `tests/test_query_analysis.py` |
| **4** | **Visual detection retrieval node** | `app/copilot/nodes/visual_retrieval.py` (`visual_retrieval`), filtered SQL + YOLO snapshot runs | Evidence tab: visual camera events, detection confidence, snapshots | `tests/test_visual_node.py` |
| **5** | **Document retrieval node** | `app/copilot/nodes/document_retrieval.py` (`document_retrieval`), hybrid search (keyword + semantic) | Evidence tab: safety manual rules, inspection report excerpts | `tests/test_document_node.py` |
| **6** | **AI answer generation node** | `app/copilot/nodes/answer_generation.py` (`answer_generation`), strict grounding prompt + offline templates | Copilot Answer card with headline, citations, key facts, actions | `tests/test_generation.py` |
| **7** | **Answer validation node** | `app/copilot/nodes/answer_validation.py` (`answer_validation`), `app/copilot/validators.py` | Trust meter gauge (0-100%) + 6 rigorous automated checks list | `tests/test_validators.py` |
| **8** | **Connect all nodes using LangGraph** | `build_graph()` compiled graph, `get_graph_description()`, `/api/copilot/graph` | Mission Control Pipeline diagram animates node-by-node via SSE | `tests/test_graph_routes.py::test_node_function_mapping` |
| **9** | **Conditional routing where required** | Conditional edges in `app/copilot/graph.py` (intents, evidence check, retry loop) | Route taken is dynamically highlighted in the UI pipeline | `tests/test_graph_routes.py::test_conditional_routing` |
| **10** | **Display the final response to the user** | `app/copilot/nodes/final_response.py` (`final_response`), `app/copilot/run_store.py` | Copilot Panel, Run History replay, streaming response cards | `tests/test_copilot_api.py::test_ask_and_stream` |
