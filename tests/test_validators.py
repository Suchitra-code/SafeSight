import pytest
from app.copilot.validators import validate_answer


def test_validators_pass():
    answer_card = {
        "headline": "Zone A Safety Status",
        "answer": "Surveillance recorded 4 violations in Zone A [V1]. Mandatory policy requires protective gear [D1]."
    }
    visual_evidence = [{"id": "V1", "text": "4 violations in Zone A"}]
    document_evidence = [{"id": "D1", "snippet": "Mandatory policy requires protective gear"}]
    facts = {"total_violations": 4}
    plan = {"entities": {"zone": "Zone A"}}

    report = validate_answer(answer_card, visual_evidence, document_evidence, facts, plan)
    assert report.score >= 80
    assert report.verdict == "pass"


def test_validators_fail_unverified_numbers():
    answer_card = {
        "headline": "Zone A Status",
        "answer": "There were 9999 violations in Zone A [V1]."
    }
    visual_evidence = [{"id": "V1", "text": "4 violations in Zone A"}]
    document_evidence = []
    facts = {"total_violations": 4}
    plan = {"entities": {"zone": "Zone A"}}

    report = validate_answer(answer_card, visual_evidence, document_evidence, facts, plan)
    assert report.verdict in ("revise", "fail")
    assert any("unverified numbers" in f.lower() for f in report.feedback)
