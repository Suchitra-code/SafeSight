"""
Unit tests for the Safety Rule Engine.
Tests all requirements specified in Section 5 of the Master Prompt:
1. All safe (wearing hardhat, safety vest, goggles)
2. No helmet (wearing vest only) -> Unsafe, helmet violation
3. No vest (wearing hardhat only) -> Unsafe, vest violation
4. No people detected -> Total 0, Safe 0, Unsafe 0, Compliance 0%
5. Multiple people -> Mixed safe and unsafe
6. Overlapping boxes -> Correct spatial association
"""
import pytest
from app.services.safety_rules import analyze_safety


def test_no_people():
    """Case 1: No people detected."""
    detections = [
        {"class_name": "Hardhat", "confidence": 0.85, "bbox": [50, 50, 100, 100]}
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 0
    assert res["safe_count"] == 0
    assert res["unsafe_count"] == 0
    assert res["compliance_percent"] == 0.0
    assert len(res["violations"]) == 0


def test_all_safe():
    """Case 2: Person with helmet and safety vest is 100% compliant and Safe."""
    detections = [
        {"class_name": "Person", "confidence": 0.95, "bbox": [100, 100, 300, 600]},
        # Hardhat in top 40% (top boundary is 100 to 100 + 500*0.4 = 300)
        {"class_name": "Hardhat", "confidence": 0.90, "bbox": [160, 110, 240, 180]},
        # Safety vest in middle body
        {"class_name": "Safety Vest", "confidence": 0.88, "bbox": [130, 220, 270, 420]},
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 1
    assert res["safe_count"] == 1
    assert res["unsafe_count"] == 0
    assert res["compliance_percent"] == 100.0
    assert len(res["violations"]) == 0
    assert res["persons"][0]["status"] == "Safe"


def test_no_helmet():
    """Case 3: Person without helmet has a helmet violation and is Unsafe."""
    detections = [
        {"class_name": "Person", "confidence": 0.92, "bbox": [100, 100, 300, 600]},
        # Only vest present
        {"class_name": "Safety Vest", "confidence": 0.90, "bbox": [130, 220, 270, 420]},
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 1
    assert res["safe_count"] == 0
    assert res["unsafe_count"] == 1
    assert res["compliance_percent"] == 0.0
    assert res["persons"][0]["status"] == "Unsafe"
    types = [v["violation_type"] for v in res["violations"]]
    assert "helmet" in types


def test_no_vest():
    """Case 4: Person with helmet but missing vest has a vest violation and is Unsafe."""
    detections = [
        {"class_name": "Person", "confidence": 0.92, "bbox": [100, 100, 300, 600]},
        {"class_name": "Hardhat", "confidence": 0.90, "bbox": [160, 110, 240, 180]},
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 1
    assert res["safe_count"] == 0
    assert res["unsafe_count"] == 1
    assert res["persons"][0]["status"] == "Unsafe"
    types = [v["violation_type"] for v in res["violations"]]
    assert "vest" in types


def test_multiple_people():
    """Case 5: Multiple people with mixed compliance states."""
    detections = [
        # Person 1: Fully safe
        {"class_name": "Person", "confidence": 0.95, "bbox": [50, 100, 200, 500]},
        {"class_name": "Hardhat", "confidence": 0.90, "bbox": [90, 110, 160, 170]},
        {"class_name": "Safety Vest", "confidence": 0.90, "bbox": [70, 200, 180, 380]},

        # Person 2: No PPE at all
        {"class_name": "Person", "confidence": 0.91, "bbox": [400, 100, 550, 500]},

        # Person 3: Missing helmet
        {"class_name": "Person", "confidence": 0.93, "bbox": [700, 100, 850, 500]},
        {"class_name": "Safety Vest", "confidence": 0.89, "bbox": [720, 200, 830, 380]},
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 3
    assert res["safe_count"] == 1
    assert res["unsafe_count"] == 2
    # 1/3 ~ 33.3%
    assert res["compliance_percent"] == 33.3


def test_overlapping_boxes():
    """Case 6: Overlapping people bounding boxes correctly assign gear by centroid."""
    detections = [
        # Person A is on the left
        {"class_name": "Person", "confidence": 0.90, "bbox": [100, 100, 300, 600]},
        # Person B overlaps on the right
        {"class_name": "Person", "confidence": 0.90, "bbox": [250, 100, 450, 600]},

        # Hardhat A center cx=200, cy=140 is inside top 40% of Person A ([100..300, 100..300])
        {"class_name": "Hardhat", "confidence": 0.92, "bbox": [170, 110, 230, 170]},
        {"class_name": "Safety Vest", "confidence": 0.91, "bbox": [150, 250, 250, 450]},

        # Person B has NO hardhat and NO vest
        {"class_name": "NO-Hardhat", "confidence": 0.88, "bbox": [320, 110, 380, 170]},
    ]
    res = analyze_safety(detections, enable_goggles=False)
    assert res["total_people"] == 2
    # Person A is safe
    assert res["persons"][0]["is_safe"] is True
    # Person B is unsafe
    assert res["persons"][1]["is_safe"] is False
    assert res["safe_count"] == 1
    assert res["unsafe_count"] == 1
    assert res["compliance_percent"] == 50.0
