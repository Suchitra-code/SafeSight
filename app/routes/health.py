"""
System Health Monitoring Blueprint for SafeSight AI - Milestone 3.
Provides /api/health endpoint reporting system status across database, detector,
vector index, visual index, LLM provider, LangGraph, and checkpointer.
"""
import os
import sqlite3
from flask import Blueprint, jsonify
import config
from app.db import execute_query, is_using_mysql
from app.services import embedder
from app.llm.provider import get_llm_client

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
def get_system_health():
    """
    Returns live operational status of all system components.
    Never crashes, handles offline modes gracefully.
    """
    status = {
        "overall": "healthy",
        "milestone": "5.0",
        "theme": "Sunrise Garden",
        "copilot": "enabled",
        "components": {}
    }

    # 1. Database Check
    try:
        db_res = execute_query("SELECT 1 as ok", fetch=True)
        db_connected = bool(db_res and len(db_res) > 0)
        status["components"]["database"] = {
            "status": "online" if db_connected else "degraded",
            "type": "MySQL (Pooled)" if is_using_mysql() else "SQLite (Fallback)",
            "ok": db_connected
        }
    except Exception as e:
        status["components"]["database"] = {"status": "offline", "error": str(e), "ok": False}
        status["overall"] = "degraded"

    # 2. YOLOv8 Detector Check
    try:
        model_exists = os.path.exists(config.MODEL_PATH)
        status["components"]["detector"] = {
            "status": "weights_loaded" if model_exists else "demo_simulation",
            "model_path": config.MODEL_PATH,
            "demo_mode": not model_exists,
            "ok": True
        }
    except Exception as e:
        status["components"]["detector"] = {"status": "error", "error": str(e), "ok": False}

    # 3. Knowledge Base Vector Index Check (Milestone 2)
    try:
        kb_status = embedder.get_embedder_status()
        status["components"]["document_index"] = {
            "status": "online",
            "backend": kb_status.get("backend"),
            "chunks_count": kb_status.get("chunk_count", 0),
            "is_neural": kb_status.get("is_neural", False),
            "ok": True
        }
    except Exception as e:
        status["components"]["document_index"] = {"status": "error", "error": str(e), "ok": False}

    # 4. Visual Event Index Check (Milestone 3)
    try:
        vis_index_exists = os.path.exists(config.FAISS_VISUAL_INDEX_PATH)
        vis_chunks_res = execute_query("SELECT count(*) as cnt FROM visual_chunks", fetch=True)
        vis_count = vis_chunks_res[0]["cnt"] if vis_chunks_res else 0
        status["components"]["visual_index"] = {
            "status": "online",
            "index_file_exists": vis_index_exists,
            "indexed_events": vis_count,
            "ok": True
        }
    except Exception as e:
        status["components"]["visual_index"] = {"status": "error", "error": str(e), "ok": False}

    # 5. LLM Provider Check
    try:
        llm = get_llm_client()
        is_avail = llm.is_available()
        status["components"]["llm_provider"] = {
            "status": "online" if is_avail else "offline_mode",
            "provider": llm.name,
            "model": config.LLM_MODEL if is_avail else "extractive_rules",
            "is_available": is_avail,
            "ok": True
        }
    except Exception as e:
        status["components"]["llm_provider"] = {"status": "error", "error": str(e), "ok": False}

    # 6. LangGraph & Checkpointer Check
    try:
        import langgraph
        import importlib.metadata
        from langgraph.checkpoint.sqlite import SqliteSaver
        try:
            lg_ver = importlib.metadata.version("langgraph")
        except Exception:
            lg_ver = getattr(langgraph, "__version__", "1.x")

        checkpointer_db = config.AGENT_CHECKPOINT_DB_PATH
        checkpointer_ok = os.path.exists(os.path.dirname(checkpointer_db))
        status["components"]["langgraph"] = {
            "status": "available",
            "version": lg_ver,
            "checkpointer": "sqlite",
            "db_path": checkpointer_db,
            "ok": True
        }
    except Exception as e:
        status["components"]["langgraph"] = {"status": "error", "error": str(e), "ok": False}
        status["overall"] = "degraded"

    # 7. Copilot Graph Compilation & Run Count (Milestone 4)
    try:
        from app.copilot.graph import build_graph
        graph = build_graph()
        graph_ok = graph is not None
        run_count_res = execute_query(
            "SELECT COUNT(*) as cnt FROM copilot_runs", fetch=True
        )
        run_count = run_count_res[0].get("cnt", 0) if run_count_res else 0
        status["components"]["copilot_graph"] = {
            "status": "compiled" if graph_ok else "error",
            "runs_total": run_count,
            "ok": graph_ok
        }
    except Exception as e:
        status["components"]["copilot_graph"] = {
            "status": "error",
            "error": str(e),
            "ok": False
        }

    # 8. Color System Check (Milestone 5)
    try:
        from tools.check_colors import check_all_colors
        violations = check_all_colors()
        status["components"]["theme_colors"] = {
            "status": "compliant" if len(violations) == 0 else "violations_found",
            "violations_count": len(violations),
            "theme": "Sunrise Garden (Strict No-Black No-Blue)",
            "ok": len(violations) == 0
        }
    except Exception as e:
        status["components"]["theme_colors"] = {"status": "error", "error": str(e), "ok": False}

    return jsonify(status), 200
