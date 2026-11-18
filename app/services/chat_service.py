"""
Chat Service for SafeSight AI - Milestone 3.
Manages chat sessions, persists and retrieves conversation history,
and records user feedback on answers.
"""
import uuid
import json
import logging
from typing import List, Dict, Any, Optional

from app.db import execute_query, execute_insert

logger = logging.getLogger(__name__)


def create_session() -> str:
    """Generates a unique session identifier for the chat interface."""
    return f"session_{uuid.uuid4().hex[:12]}"


def get_history(session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Retrieves the last `limit` chat messages for a given session.
    Returns structured list with parsed sources.
    """
    if not session_id:
        return []
    try:
        rows = execute_query(
            """
            SELECT id, session_id, role, content, mode_used, confidence,
                   latency_ms, sources_json, feedback, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY id ASC
            LIMIT %s
            """,
            (session_id, limit),
            fetch=True
        ) or []

        results = []
        for r in rows:
            item = dict(r)
            # Parse sources JSON if present
            raw_sources = item.get("sources_json")
            if raw_sources and isinstance(raw_sources, str):
                try:
                    item["sources"] = json.loads(raw_sources)
                except Exception:
                    item["sources"] = []
            elif isinstance(raw_sources, list):
                item["sources"] = raw_sources
            else:
                item["sources"] = []

            results.append(item)
        return results
    except Exception as e:
        logger.warning(f"Error fetching chat history for session {session_id}: {e}")
        return []


def set_feedback(msg_id: Any, feedback: int) -> bool:
    """
    Updates the feedback score (1 for thumbs up, -1 for thumbs down) for a chat message.
    """
    try:
        mid = int(msg_id)
        fb = int(feedback)
        execute_query(
            "UPDATE chat_messages SET feedback = %s WHERE id = %s",
            (fb, mid),
            commit=True
        )
        return True
    except Exception as e:
        logger.warning(f"Error updating feedback for msg_id {msg_id}: {e}")
        return False
