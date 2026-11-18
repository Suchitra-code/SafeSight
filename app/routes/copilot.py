"""
REST & Streaming API Routes for SafeSight Copilot (Milestone 4).
Endpoints:
- POST /api/copilot/ask: kicks off graph in background, returns run_id
- GET  /api/copilot/stream/<run_id>: SSE streaming of node events & final payload
- GET  /api/copilot/runs/<run_id>: direct polling fallback
- GET  /api/copilot/history: list recent runs
- GET  /api/copilot/runs/<run_id>/events: detailed events for replay
- GET  /api/copilot/graph: graph structure description
- GET  /api/copilot/suggestions: dynamic prompt ideas
"""
import uuid
import time
import json
import threading
import queue
import logging
from collections import defaultdict
from flask import Blueprint, request, jsonify, Response, current_app

from app.copilot.events import register_run, get_run_queue, cleanup_run, publish_event
from app.copilot.graph import build_graph, get_graph_description
from app.copilot.run_store import get_copilot_run, list_recent_runs, get_run_events
from app.copilot.suggestions import get_suggested_questions
import config

logger = logging.getLogger(__name__)

copilot_bp = Blueprint("copilot_api", __name__, url_prefix="/api/copilot")

# Compiled graph singleton
_COPILOT_GRAPH = None

# ---------------------------------------------------------------------------
# Simple per-session rate limiter (sliding window, in-memory)
# ---------------------------------------------------------------------------
_rate_buckets: dict = defaultdict(list)  # session_id → [timestamp, …]
_RATE_LOCK = threading.Lock()


def _check_rate_limit(session_id: str) -> bool:
    """Return True if the request is within the rate limit, False otherwise."""
    limit = getattr(config, "COPILOT_RATE_LIMIT_PER_MIN", 20)
    now = time.time()
    window = 60.0  # seconds

    with _RATE_LOCK:
        bucket = _rate_buckets[session_id]
        # Prune old entries
        _rate_buckets[session_id] = [t for t in bucket if now - t < window]
        if len(_rate_buckets[session_id]) >= limit:
            return False
        _rate_buckets[session_id].append(now)
        return True


def get_graph():
    global _COPILOT_GRAPH
    if _COPILOT_GRAPH is None:
        _COPILOT_GRAPH = build_graph()
    return _COPILOT_GRAPH


def _execute_graph_thread(run_id: str, initial_state: dict):
    """Executes the LangGraph compiled pipeline inside a dedicated background thread."""
    publish_event(run_id, "run_started", {
        "question": initial_state.get("question"),
        "timestamp": time.time()
    })

    try:
        graph = get_graph()
        # Invoke compiled StateGraph with recursion limit
        final_state = graph.invoke(initial_state, {"recursion_limit": 25})
    except Exception as e:
        logger.error(f"Error during graph execution for run {run_id}: {e}", exc_info=True)
        publish_event(run_id, "error", {"error": str(e)})


@copilot_bp.route("/ask", methods=["POST"])
def ask_copilot():
    """Validates query, initializes run state, and launches graph execution."""
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    session_id = data.get("session_id") or str(uuid.uuid4())[:8]
    ui_context = data.get("ui_context") or {}
    image_path = data.get("image_path")

    # Rate limit check
    if not _check_rate_limit(session_id):
        return jsonify({
            "success": False,
            "error": "Rate limit exceeded. Please wait a moment before asking again."
        }), 429

    run_id = f"run_{uuid.uuid4().hex[:10]}"

    # Register in-memory queue for streaming
    register_run(run_id)

    initial_state = {
        "run_id": run_id,
        "session_id": session_id,
        "question": question,
        "image_path": image_path,
        "ui_context": ui_context,
        "history": data.get("history", []),
        "language": "en",
        "retries": 0,
        "validator_feedback": [],
        "route": [],
        "trace": [],
        "mode": "offline"
    }

    # Start graph in background daemon thread
    t = threading.Thread(
        target=_execute_graph_thread,
        args=(run_id, initial_state),
        daemon=True
    )
    t.start()

    return jsonify({
        "success": True,
        "run_id": run_id,
        "session_id": session_id,
        "stream_url": f"/api/copilot/stream/{run_id}"
    }), 202


@copilot_bp.route("/stream/<run_id>", methods=["GET"])
def stream_copilot(run_id):
    """Server-Sent Events (SSE) streaming endpoint."""
    q = get_run_queue(run_id)

    def event_generator():
        # Keep connection open for events
        max_wait = 45  # seconds max
        start_wait = time.time()

        while time.time() - start_wait < max_wait:
            if q is None:
                # Check if already completed in DB
                run_data = get_copilot_run(run_id)
                if run_data:
                    yield f"event: final\ndata: {json.dumps(run_data)}\n\n"
                break

            try:
                event = q.get(timeout=1.0)
                event_type = event.get("event_type", "message")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

                if event_type in ("final", "error"):
                    break
            except queue.Empty:
                # Send periodic heartbeat to keep SSE connection alive
                yield ": heartbeat\n\n"

        cleanup_run(run_id)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@copilot_bp.route("/runs/<run_id>", methods=["GET"])
def get_run_status(run_id):
    """Direct polling fallback if SSE is unavailable in browser."""
    run_data = get_copilot_run(run_id)
    if not run_data:
        # Check if currently running
        if get_run_queue(run_id) is not None:
            return jsonify({"status": "running", "run_id": run_id})
        return jsonify({"error": "Run not found"}), 404
    return jsonify({"status": "completed", "run": run_data})


@copilot_bp.route("/history", methods=["GET"])
def get_history():
    """Returns recent Copilot runs for Mission Control."""
    limit = int(request.args.get("limit", 15))
    runs = list_recent_runs(limit=limit)
    return jsonify({"runs": runs})


@copilot_bp.route("/runs/<run_id>/events", methods=["GET"])
def get_events(run_id):
    """Returns detailed event timeline for a run for replay."""
    events = get_run_events(run_id)
    return jsonify({"run_id": run_id, "events": events})


@copilot_bp.route("/graph", methods=["GET"])
def get_graph_meta():
    """Returns exact nodes and edges structure of compiled LangGraph workflow."""
    return jsonify(get_graph_description())


@copilot_bp.route("/suggestions", methods=["GET"])
def get_suggestions():
    """Returns dynamic query ideas based on active database telemetry."""
    return jsonify({"suggestions": get_suggested_questions()})
