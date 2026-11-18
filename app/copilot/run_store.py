"""
Database persistence for SafeSight Copilot runs and events (Milestone 4).
Supports SQLite and MySQL with clean fallback and structured JSON serialization.
"""
import json
import logging
from typing import Dict, Any, List, Optional
from app.db import execute_insert, execute_query

logger = logging.getLogger(__name__)


def save_copilot_run(final_data: Dict[str, Any]) -> bool:
    """Saves a completed Copilot run into the database."""
    try:
        run_id = final_data.get("run_id", "")
        session_id = final_data.get("session_id", "default_session")
        question = final_data.get("question", "")
        mode = final_data.get("mode", "offline")
        intent = final_data.get("intent", "general")
        route = json.dumps(final_data.get("route", []))

        val = final_data.get("validation", {})
        validation_score = val.get("score", 0)
        validation_verdict = val.get("verdict", "pass")

        card = final_data.get("answer_card", {})
        headline = card.get("headline", "")
        answer_text = card.get("answer", "")
        key_facts = json.dumps(card.get("key_facts", []))
        actions = json.dumps(card.get("recommended_actions", []))

        # Calculate total duration from trace
        trace = final_data.get("trace", [])
        total_duration = sum(t.get("duration_ms", 0.0) for t in trace)

        sql = """
            INSERT OR REPLACE INTO copilot_runs (
                run_id, session_id, question, mode, intent, route,
                validation_score, validation_verdict, answer_headline,
                answer_text, key_facts, actions, total_duration_ms
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            run_id, session_id, question, mode, intent, route,
            validation_score, validation_verdict, headline,
            answer_text, key_facts, actions, total_duration
        )
        execute_insert(sql, params)
        return True
    except Exception as e:
        logger.error(f"Error saving copilot run {final_data.get('run_id')}: {e}")
        return False


def log_copilot_event(
    run_id: str,
    event_type: str,
    node_name: Optional[str] = None,
    duration_ms: float = 0.0,
    summary: str = "",
    payload: str = ""
):
    """Logs an intermediate streaming event to the database."""
    try:
        sql = """
            INSERT INTO copilot_events (run_id, event_type, node_name, duration_ms, summary, payload)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        execute_insert(sql, (run_id, event_type, node_name, duration_ms, summary, payload))
    except Exception as e:
        logger.warning(f"Failed to log copilot event: {e}")


def get_copilot_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a saved copilot run by run_id."""
    try:
        rows = execute_query("SELECT * FROM copilot_runs WHERE run_id = %s", (run_id,), fetch=True)
        if not rows:
            return None
        row = dict(rows[0])
        try:
            row["route"] = json.loads(row.get("route") or "[]")
        except Exception:
            row["route"] = []
        try:
            row["key_facts"] = json.loads(row.get("key_facts") or "[]")
        except Exception:
            row["key_facts"] = []
        try:
            row["actions"] = json.loads(row.get("actions") or "[]")
        except Exception:
            row["actions"] = []
        return row
    except Exception as e:
        logger.error(f"Error fetching copilot run {run_id}: {e}")
        return None


def list_recent_runs(limit: int = 15) -> List[Dict[str, Any]]:
    """Returns recent copilot runs for mission control history & replay."""
    try:
        rows = execute_query(
            "SELECT * FROM copilot_runs ORDER BY created_at DESC LIMIT %s",
            (limit,), fetch=True
        ) or []
        res = []
        for r in rows:
            d = dict(r)
            try:
                d["route"] = json.loads(d.get("route") or "[]")
            except Exception:
                d["route"] = []
            try:
                d["key_facts"] = json.loads(d.get("key_facts") or "[]")
            except Exception:
                d["key_facts"] = []
            try:
                d["actions"] = json.loads(d.get("actions") or "[]")
            except Exception:
                d["actions"] = []
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            res.append(d)
        return res
    except Exception as e:
        logger.error(f"Error listing copilot runs: {e}")
        return []


def get_run_events(run_id: str) -> List[Dict[str, Any]]:
    """Retrieves all logged events for a given run_id for replay."""
    try:
        rows = execute_query(
            "SELECT * FROM copilot_events WHERE run_id = %s ORDER BY id ASC",
            (run_id,), fetch=True
        ) or []
        events = []
        for r in rows:
            d = dict(r)
            if d.get("created_at"):
                d["created_at"] = str(d["created_at"])
            events.append(d)
        return events
    except Exception as e:
        logger.error(f"Error fetching events for run {run_id}: {e}")
        return []
