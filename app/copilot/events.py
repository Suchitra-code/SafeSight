"""
Event bus & traced() decorator for SafeSight Copilot live telemetry streaming.
Maintains in-memory thread-safe queues per run_id for real-time SSE.
"""
import time
import functools
import queue
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Active event queues keyed by run_id
_RUN_QUEUES: Dict[str, queue.Queue] = {}


def register_run(run_id: str) -> queue.Queue:
    """Registers an event queue for a new copilot run."""
    q = queue.Queue(maxsize=100)
    _RUN_QUEUES[run_id] = q
    return q


def get_run_queue(run_id: str) -> Optional[queue.Queue]:
    """Retrieves the event queue for an active run."""
    return _RUN_QUEUES.get(run_id)


def cleanup_run(run_id: str):
    """Cleans up the queue once run completes or aborts."""
    if run_id in _RUN_QUEUES:
        del _RUN_QUEUES[run_id]


def publish_event(run_id: str, event_type: str, payload: Dict[str, Any]):
    """Pushes a typed event into the run's streaming queue and persists to DB if available."""
    q = _RUN_QUEUES.get(run_id)
    event_data = {
        "run_id": run_id,
        "event_type": event_type,
        "timestamp": time.time(),
        **payload
    }
    if q:
        try:
            q.put_nowait(event_data)
        except queue.Full:
            logger.warning(f"Event queue full for run {run_id}, dropping event {event_type}")

    # Async / try-catch DB log
    try:
        from app.copilot.run_store import log_copilot_event
        log_copilot_event(
            run_id=run_id,
            event_type=event_type,
            node_name=payload.get("node_name"),
            duration_ms=payload.get("duration_ms", 0.0),
            summary=payload.get("summary", ""),
            payload=str(payload)
        )
    except Exception:
        pass


def traced(node_name: str):
    """
    Decorator for LangGraph nodes.
    Publishes node_started and node_finished events with timing and status.
    Catches unexpected exceptions to guarantee graph never crashes.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            run_id = state.get("run_id", "unknown_run")
            start_t = time.time()

            publish_event(run_id, "node_started", {
                "node_name": node_name,
                "summary": f"Executing node {node_name}..."
            })

            try:
                result = func(state, *args, **kwargs)
                duration_ms = round((time.time() - start_t) * 1000.0, 2)
                summary = result.get("summary", f"Completed {node_name}") if isinstance(result, dict) else f"Completed {node_name}"

                publish_event(run_id, "node_finished", {
                    "node_name": node_name,
                    "duration_ms": duration_ms,
                    "summary": summary
                })

                trace_item = {
                    "node": node_name,
                    "duration_ms": duration_ms,
                    "summary": summary
                }

                # Ensure route and trace are appended safely
                out_dict = dict(result) if isinstance(result, dict) else {}
                out_dict.setdefault("route", [node_name])
                out_dict.setdefault("trace", [trace_item])
                return out_dict

            except Exception as e:
                duration_ms = round((time.time() - start_t) * 1000.0, 2)
                logger.error(f"Error executing copilot node {node_name}: {e}", exc_info=True)
                publish_event(run_id, "node_finished", {
                    "node_name": node_name,
                    "duration_ms": duration_ms,
                    "summary": f"Failed {node_name}: {str(e)}",
                    "error": str(e)
                })
                return {
                    "error": f"Node {node_name} failed: {str(e)}",
                    "route": [node_name],
                    "trace": [{
                        "node": node_name,
                        "duration_ms": duration_ms,
                        "summary": f"Error: {str(e)}"
                    }]
                }
        return wrapper
    return decorator
