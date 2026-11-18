"""
app.copilot — SafeSight Copilot package (Milestone 4).

This package implements the LangGraph-based multi-node pipeline that answers
safety questions by combining visual detection data with document knowledge,
validates its own answers, and streams results live via SSE.

Submodules
----------
state           CopilotState TypedDict with annotated reducers.
schemas         Pydantic models for query plans, answers, validation.
events          In-memory per-run event bus and @traced decorator.
run_store       MySQL/SQLite persistence for runs and events.
graph           build_graph() — the compiled LangGraph StateGraph.
validators      Six-check answer validation engine.
offline_templates   Deterministic answer generation (no LLM needed).
suggestions     Smart suggested questions from live data.
nodes/          Individual graph node implementations.
"""
