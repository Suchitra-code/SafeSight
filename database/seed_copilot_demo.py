"""
Seed realistic demo data for SafeSight Copilot & Mission Control (Milestone 4).
Populates site zones, historical copilot runs, and realistic visual/knowledge telemetry.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import uuid
from app.db import execute_insert, execute_query


def seed_milestone4_data():
    """Seeds sample data for Mission Control demonstrations."""
    # 1. Seed Site Zones
    zones = [
        ("zone_a", "Zone A", "Fabrication & Heavy Machinery Workshop", "HIGH", "50,50 350,50 350,300 50,300"),
        ("zone_b", "Zone B", "Assembly, Staging & Tool Crib", "LOW", "400,50 750,50 750,300 400,300"),
        ("exit_gate", "Exit Gate", "Exit Gate & Logistics Loading Dock", "MEDIUM", "150,350 650,350 650,470 150,470")
    ]
    for zid, name, desc, risk, poly in zones:
        execute_insert(
            "INSERT OR REPLACE INTO site_zones (zone_id, name, description, risk_level, svg_coords) VALUES (%s, %s, %s, %s, %s)",
            (zid, name, desc, risk, poly)
        )

    # 2. Seed a sample benchmark copilot run for history and replay
    sample_run_id = "run_demo_benchmark_01"
    existing = execute_query("SELECT run_id FROM copilot_runs WHERE run_id = %s", (sample_run_id,), fetch=True)
    if not existing:
        execute_insert(
            """
            INSERT INTO copilot_runs (
                run_id, session_id, question, mode, intent, route,
                validation_score, validation_verdict, answer_headline,
                answer_text, key_facts, actions, total_duration_ms
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                sample_run_id, "session_benchmark",
                "What are the top safety infractions in Zone A today and what does the policy mandate?",
                "offline", "both",
                '["query_analysis", "visual_retrieval", "document_retrieval", "evidence_check", "answer_generation", "answer_validation", "final_response"]',
                95, "pass",
                "Site Audit: 6 Infractions Flagged in Zone A Against Mandated PPE Rules",
                "Surveillance cameras recorded 6 safety violations in Zone A with an overall compliance score of 91.2% [V1]. Under Corporate PPE Manual standards [Corporate PPE Manual, p.14], all active personnel must wear certified hardhats and high-visibility vests [D1]. Immediate supervisor briefing is advised to remediate observed equipment gaps and ensure compliance [V1].",
                '[{"label": "Monitored Workers", "value": "42", "cite": "V1"}, {"label": "Compliance Rate", "value": "91.2%", "cite": "V1"}, {"label": "Infractions", "value": "6", "cite": "V1"}]',
                '[{"action": "Dispatch safety supervisor to Zone A to brief workers.", "cite": "V1"}, {"action": "Review mandatory gear standards in [Corporate PPE Manual, p.14].", "cite": "D1"}]',
                245.5
            )
        )

        # Seed event trace for replay
        trace_events = [
            ("node_started", "query_analysis", 0.0, "Analyzing query intent & filters..."),
            ("node_finished", "query_analysis", 18.2, "Identified intent: both, zone: Zone A"),
            ("node_started", "visual_retrieval", 0.0, "Searching camera detection records..."),
            ("node_finished", "visual_retrieval", 62.4, "Retrieved 5 visual events for Zone A"),
            ("node_started", "document_retrieval", 0.0, "Hybrid search over safety manuals..."),
            ("node_finished", "document_retrieval", 54.1, "Retrieved 4 relevant policy chunks"),
            ("node_started", "evidence_check", 0.0, "Checking evidence threshold..."),
            ("node_finished", "evidence_check", 3.2, "Evidence threshold passed"),
            ("node_started", "answer_generation", 0.0, "Synthesizing answer card..."),
            ("node_finished", "answer_generation", 45.8, "Answer generated with 3 citations"),
            ("node_started", "answer_validation", 0.0, "Running Trust Meter checks..."),
            ("node_finished", "answer_validation", 28.6, "Validation passed: 95% trust score"),
            ("node_started", "final_response", 0.0, "Persisting response payload..."),
            ("node_finished", "final_response", 12.1, "Mission Control response ready")
        ]

        for etype, nname, dur, summ in trace_events:
            execute_insert(
                "INSERT INTO copilot_events (run_id, event_type, node_name, duration_ms, summary, payload) VALUES (%s, %s, %s, %s, %s, %s)",
                (sample_run_id, etype, nname, dur, summ, "{}")
            )

    print("Milestone 4 demo data seeded successfully!")


if __name__ == "__main__":
    seed_milestone4_data()
