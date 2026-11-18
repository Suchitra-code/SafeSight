import pytest
from app.copilot.nodes.document_retrieval import document_retrieval


def test_document_retrieval():
    state = {
        "run_id": "test_doc_run",
        "question": "What is the mandatory PPE policy for helmet safety?",
        "plan": {
            "entities": {
                "ppe_type": "Hardhat"
            }
        }
    }
    res = document_retrieval(state)
    assert "document_evidence" in res
    assert isinstance(res["document_evidence"], list)
