"""
Agent Runner Service for SafeSight AI - Milestone 3.
Manages asynchronous and interactive execution of LangGraph workflows,
persisting checkpoints to SQLite and tracking execution states.
"""
import uuid
import logging
import sqlite3
import threading
from typing import Dict, Any, List, Optional

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:
    try:
        from langgraph_checkpoint_sqlite import SqliteSaver
    except ImportError:
        from langgraph.checkpoint.memory import MemorySaver as SqliteSaver

import config
from app.db import execute_query, execute_insert
from app.agents.investigation_graph import create_investigation_graph, update_run_db

logger = logging.getLogger(__name__)

_runner_lock = threading.Lock()
_graph_instance = None
_checkpointer_conn = None


def get_checkpointer():
    """Initializes and returns a persistent SqliteSaver checkpointer."""
    global _checkpointer_conn
    try:
        if _checkpointer_conn is None:
            _checkpointer_conn = sqlite3.connect(
                config.AGENT_CHECKPOINT_DB_PATH,
                check_same_thread=False
            )
        return SqliteSaver(_checkpointer_conn)
    except Exception as e:
        logger.warning(f"Could not initialize SQLite checkpointer: {e}")
        return None


def get_compiled_graph():
    """Returns the compiled investigation graph with checkpointer and human-review interrupt."""
    global _graph_instance
    if _graph_instance is None:
        cp = get_checkpointer()
        _graph_instance = create_investigation_graph(checkpointer=cp)
    return _graph_instance


def start_investigation_run(violation_id: int) -> Dict[str, Any]:
    """
    Initiates an incident investigation for a given violation.
    Returns existing run if already active to prevent duplicate runs.
    """
    with _runner_lock:
        # Prevent duplicate active investigations
        active = execute_query(
            """SELECT run_id, status FROM investigation_runs
               WHERE violation_id = %s AND status NOT IN ('completed', 'failed', 'dismissed')
               ORDER BY id DESC LIMIT 1""",
            (violation_id,),
            fetch=True
        )
        if active:
            return {
                "run_id": active[0]["run_id"],
                "status": active[0]["status"],
                "is_new": False,
                "message": "Existing active investigation returned."
            }

        run_id = f"run_{uuid.uuid4().hex[:8]}"
        try:
            execute_insert(
                """INSERT INTO investigation_runs (run_id, violation_id, status, current_node)
                   VALUES (%s, %s, 'running', 'load_event')""",
                (run_id, violation_id)
            )
        except Exception as e:
            logger.error(f"Failed to record investigation run {run_id}: {e}")
            return {"error": str(e), "status": "failed"}

    # Run the graph up to the human_review interrupt
    graph = get_compiled_graph()
    initial_state = {
        "run_id": run_id,
        "violation_id": violation_id,
        "trace": []
    }
    config_dict = {"configurable": {"thread_id": run_id}}

    try:
        # Run until human_review interrupt
        for chunk in graph.stream(initial_state, config_dict):
            pass
        update_run_db(run_id, status="waiting_approval", current_node="human_review")
        return {
            "run_id": run_id,
            "status": "waiting_approval",
            "is_new": True,
            "message": "Investigation reached supervisor review stage."
        }
    except Exception as e:
        logger.error(f"Error during investigation execution for {run_id}: {e}")
        update_run_db(run_id, status="failed", current_node="error")
        return {"run_id": run_id, "status": "failed", "error": str(e)}


def resume_investigation_run(run_id: str, decision: str, notes: str = "") -> Dict[str, Any]:
    """
    Resumes an investigation paused at human_review, applying supervisor decision.
    `decision`: 'approved' | 'rejected'
    """
    graph = get_compiled_graph()
    config_dict = {"configurable": {"thread_id": run_id}}

    approval_dict = {
        "decision": decision,
        "notes": notes
    }

    try:
        # Update graph state with approval decision and resume
        graph.update_state(config_dict, {"approval": approval_dict})
        for chunk in graph.stream(None, config_dict):
            pass

        final_status = "completed" if decision == "approved" else "dismissed"
        update_run_db(run_id, status=final_status, approval_status=decision, supervisor_notes=notes)
        return {
            "run_id": run_id,
            "status": final_status,
            "approval_status": decision,
            "message": f"Investigation resumed and {final_status}."
        }
    except Exception as e:
        logger.error(f"Error resuming investigation run {run_id}: {e}")
        update_run_db(run_id, status="failed")
        return {"run_id": run_id, "status": "failed", "error": str(e)}


def get_run_status(run_id: str) -> Optional[Dict[str, Any]]:
    """Returns comprehensive run status, including state fields and execution trace steps."""
    runs = execute_query(
        "SELECT * FROM investigation_runs WHERE run_id = %s",
        (run_id,),
        fetch=True
    )
    if not runs:
        return None

    run_info = dict(runs[0])
    v_id = run_info.get("violation_id")
    v_data = execute_query("SELECT * FROM violations WHERE id = %s", (v_id,), fetch=True)
    run_info["violation"] = dict(v_data[0]) if v_data else {}

    # Fetch agent steps for trace visualization
    steps = execute_query(
        """SELECT node_name, input_summary, output_summary, status, duration_ms, created_at
           FROM agent_steps WHERE run_id = %s ORDER BY id ASC""",
        (run_id,),
        fetch=True
    ) or []
    run_info["steps"] = [dict(s) for s in steps]
    return run_info


def list_investigations(page: int = 1, per_page: int = 20) -> Dict[str, Any]:
    """Lists investigations paginated with associated violation details."""
    offset = max(0, (page - 1) * per_page)
    count_res = execute_query("SELECT COUNT(*) as total FROM investigation_runs", fetch=True)
    total = count_res[0]["total"] if count_res else 0

    rows = execute_query(
        """SELECT r.*, v.camera_name as camera, v.location, v.violation_type, v.severity as v_severity, v.detected_at as v_detected_at, v.snapshot_path
           FROM investigation_runs r
           LEFT JOIN violations v ON r.violation_id = v.id
           ORDER BY r.id DESC
           LIMIT %s OFFSET %s""",
        (per_page, offset),
        fetch=True
    ) or []

    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total > 0 else 1
    }
