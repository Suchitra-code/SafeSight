"""
Dynamic query suggestions for SafeSight Copilot based on live system state.
"""
from typing import List
from app.db import execute_query


def get_suggested_questions() -> List[str]:
    """Returns contextual safety questions tailored to active database telemetry."""
    suggestions = [
        "What are the top safety infractions recorded today across all zones?",
        "Are workers in Zone A compliant with helmet and safety vest requirements?",
        "What do site safety manuals require for crane and elevated work areas?",
        "How many PPE violations were detected over the past 7 days?",
        "What corrective actions does the safety policy mandate for repeated vest violations?"
    ]

    try:
        # Check if there is an active high severity violation
        rows = execute_query(
            "SELECT camera_name, violation_type FROM violations WHERE severity = 'HIGH' ORDER BY id DESC LIMIT 1",
            fetch=True
        )
        if rows:
            cam = rows[0].get("camera_name", "Cam 01")
            vtype = rows[0].get("violation_type", "Hardhat")
            suggestions.insert(0, f"Explain the recent high-severity {vtype} violation detected by {cam}.")
    except Exception:
        pass

    return suggestions[:5]
