import pytest
from app.copilot.nodes.answer_generation import answer_generation


def test_answer_generation_offline():
    state = {
        "run_id": "test_gen_run",
        "question": "What is the compliance rate in Zone A?",
        "plan": {"intent": "both", "entities": {"zone": "Zone A"}},
        "facts": {"total_violations": 4, "compliance_percent": 92.5, "total_workers_detected": 40},
        "visual_evidence": [{"id": "V1", "text": "4 violations in Zone A"}],
        "document_evidence": [{"id": "D1", "title": "Safety Manual", "page": 1, "snippet": "Wear hardhats."}],
        "retries": 0
    }
    res = answer_generation(state)
    assert "answer_card" in res
    card = res["answer_card"]
    assert "headline" in card
    assert "answer" in card
    assert "[V1]" in card["answer"] or "[D1]" in card["answer"]
