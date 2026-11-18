import pytest
from app.copilot.nodes.query_analysis import query_analysis


def test_query_analysis_smalltalk():
    state = {"question": "Hello good morning!"}
    res = query_analysis(state)
    plan = res["plan"]
    assert plan["intent"] == "smalltalk"


def test_query_analysis_out_of_scope():
    state = {"question": "What is the weather in Paris?"}
    res = query_analysis(state)
    plan = res["plan"]
    assert plan["intent"] == "out_of_scope"


def test_query_analysis_entities_and_intents():
    state = {
        "question": "How many helmet violations were detected today in Zone A?",
        "ui_context": {}
    }
    res = query_analysis(state)
    plan = res["plan"]
    assert plan["needs_visual"] is True
    assert plan["entities"].get("zone") == "Zone A"
    assert plan["entities"].get("violation_type") == "Hardhat"
    assert "date_from" in plan["entities"]
