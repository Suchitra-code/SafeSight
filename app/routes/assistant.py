"""Assistant API routes for Milestone 3.
Provides POST /api/assistant/ask and related endpoints.
All routes are wrapped in try/except to avoid stack traces.
"""

from flask import Blueprint, request, jsonify, current_app
import logging

from app.rag.rag_pipeline import answer_rag_question
from app.services import chat_service

assistant_bp = Blueprint('assistant', __name__, url_prefix='/api/assistant')
logger = logging.getLogger(__name__)

@assistant_bp.route('/ask', methods=['POST'])
def ask_question():
    try:
        data = request.get_json(silent=True) or {}
        question = data.get('question', '').strip()
        session_id = data.get('session_id') or chat_service.create_session()
        filters = data.get('filters') or {}
        if not question:
            return jsonify({'error': 'Question required'}), 400
        result = answer_rag_question(question, session_id=session_id, filters=filters)
        return jsonify(result)
    except Exception as e:
        logger.exception('Assistant ask error')
        return jsonify({'error': str(e)}), 500

@assistant_bp.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    try:
        hist = chat_service.get_history(session_id, limit=20)
        return jsonify({'messages': hist})
    except Exception as e:
        logger.exception('Assistant history error')
        return jsonify({'error': str(e)}), 500

@assistant_bp.route('/feedback/<msg_id>', methods=['POST'])
def feedback(msg_id):
    try:
        data = request.get_json(silent=True) or {}
        fb = data.get('feedback')
        if fb not in [1, -1]:
            return jsonify({'error': 'Invalid feedback'}), 400
        chat_service.set_feedback(msg_id, fb)
        return jsonify({'status': 'ok'})
    except Exception as e:
        logger.exception('Assistant feedback error')
        return jsonify({'error': str(e)}), 500
