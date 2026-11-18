import pytest
from app.copilot.nodes.visual_retrieval import visual_retrieval


def test_visual_retrieval_facts():
    state = {
        "run_id": "test_vis_run",
        "plan": {
            "entities": {
                "zone": "Zone A",
                "violation_type": "Hardhat"
            }
        }
    }
    res = visual_retrieval(state)
    assert "visual_evidence" in res
    assert "facts" in res
    assert "compliance_percent" in res["facts"]
    assert "total_violations" in res["facts"]
