"""
Safety Rule Engine for SafeSight AI.
Matches detected PPE gear to persons based on geometric containment
and determines compliance, safe/unsafe status, and violations.
"""
from typing import List, Dict, Any
import config


def get_box_center(bbox: List[int]) -> tuple:
    """Returns the (cx, cy) center of a bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def point_in_bbox(cx: float, cy: float, bbox: List[int]) -> bool:
    """Checks if point (cx, cy) is inside bounding box [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = bbox
    return (x1 <= cx <= x2) and (y1 <= cy <= y2)


def point_in_top_ratio(cx: float, cy: float, bbox: List[int], ratio: float) -> bool:
    """Checks if point (cx, cy) is inside the top fraction (ratio) of a bounding box."""
    x1, y1, x2, y2 = bbox
    h = y2 - y1
    top_limit = y1 + (h * ratio)
    return (x1 <= cx <= x2) and (y1 <= cy <= top_limit)


def analyze_safety(detections: List[Dict[str, Any]], enable_goggles: bool = None) -> Dict[str, Any]:
    """
    Evaluates safety rules for detected people and PPE items.

    Args:
        detections: List of dicts with 'class_name', 'confidence', 'bbox' ([x1, y1, x2, y2])
        enable_goggles: Whether to check goggles compliance (defaults to config.ENABLE_GOGGLES_CHECK)

    Returns:
        dict:
            total_people: int
            safe_count: int
            unsafe_count: int
            compliance_percent: float (0.0 to 100.0)
            persons: list of annotated person dicts with bbox, status, violations, matched_ppe
            violations: list of violation event dicts
    """
    if enable_goggles is None:
        enable_goggles = config.ENABLE_GOGGLES_CHECK

    # Separate persons and gear
    persons_raw = []
    ppe_items = []

    for d in detections:
        c_name = d.get("class_name", "").strip()
        if c_name.lower() == "person":
            persons_raw.append(d)
        else:
            ppe_items.append(d)

    total_people = len(persons_raw)
    if total_people == 0:
        return {
            "total_people": 0,
            "safe_count": 0,
            "unsafe_count": 0,
            "compliance_percent": 0.0,
            "persons": [],
            "violations": []
        }

    evaluated_persons = []
    all_violations = []

    for idx, p in enumerate(persons_raw):
        p_box = p["bbox"]
        p_conf = p.get("confidence", 0.9)

        matched_ppe = []
        has_hardhat = False
        has_no_hardhat = False
        has_vest = False
        has_no_vest = False
        has_goggles = False
        has_no_goggles = False

        # Match PPE items against this person
        for item in ppe_items:
            item_name = item.get("class_name", "")
            item_name_lower = item_name.lower()
            item_bbox = item["bbox"]
            item_conf = item.get("confidence", 0.0)
            cx, cy = get_box_center(item_bbox)

            # Helmet / NO-Hardhat: center in top 40% of person box
            if item_name_lower in ("hardhat", "helmet"):
                if point_in_top_ratio(cx, cy, p_box, 0.40):
                    has_hardhat = True
                    matched_ppe.append(item)
            elif item_name_lower in ("no-hardhat", "no-helmet"):
                if point_in_top_ratio(cx, cy, p_box, 0.40):
                    has_no_hardhat = True
                    matched_ppe.append(item)

            # Vest / NO-Safety Vest: center inside person box
            elif item_name_lower in ("safety vest", "vest"):
                if point_in_bbox(cx, cy, p_box):
                    has_vest = True
                    matched_ppe.append(item)
            elif item_name_lower in ("no-safety vest", "no-vest"):
                if point_in_bbox(cx, cy, p_box):
                    has_no_vest = True
                    matched_ppe.append(item)

            # Goggles / NO-Goggles: center in top 35% of person box
            elif item_name_lower in ("goggles", "glasses"):
                if point_in_top_ratio(cx, cy, p_box, 0.35):
                    has_goggles = True
                    matched_ppe.append(item)
            elif item_name_lower in ("no-goggles", "no-glasses"):
                if point_in_top_ratio(cx, cy, p_box, 0.35):
                    has_no_goggles = True
                    matched_ppe.append(item)

        # Rule Evaluations
        person_violations = []

        # If person has no matching PPE at all, treat helmet and vest as missing
        if len(matched_ppe) == 0:
            person_violations.append({
                "violation_type": "helmet",
                "severity": "HIGH",
                "confidence": p_conf,
                "person_bbox": p_box,
                "detail": "Missing Hardhat (No PPE Detected)"
            })
            person_violations.append({
                "violation_type": "vest",
                "severity": "MEDIUM",
                "confidence": p_conf,
                "person_bbox": p_box,
                "detail": "Missing Safety Vest (No PPE Detected)"
            })
            if enable_goggles:
                person_violations.append({
                    "violation_type": "goggles",
                    "severity": "MEDIUM",
                    "confidence": p_conf,
                    "person_bbox": p_box,
                    "detail": "Missing Safety Goggles"
                })
        else:
            # 1. Helmet evaluation (HIGH)
            if has_no_hardhat or (not has_hardhat):
                person_violations.append({
                    "violation_type": "helmet",
                    "severity": "HIGH",
                    "confidence": p_conf,
                    "person_bbox": p_box,
                    "detail": "No Hardhat Detected" if not has_hardhat else "Explicit NO-Hardhat Detected"
                })

            # 2. Vest evaluation (MEDIUM)
            if has_no_vest or (not has_vest):
                person_violations.append({
                    "violation_type": "vest",
                    "severity": "MEDIUM",
                    "confidence": p_conf,
                    "person_bbox": p_box,
                    "detail": "No Safety Vest Detected" if not has_vest else "Explicit NO-Vest Detected"
                })

            # 3. Goggles evaluation (MEDIUM, if enabled)
            if enable_goggles:
                if has_no_goggles or (not has_goggles):
                    person_violations.append({
                        "violation_type": "goggles",
                        "severity": "MEDIUM",
                        "confidence": p_conf,
                        "person_bbox": p_box,
                        "detail": "No Eye Protection Detected"
                    })

        # Person status is Safe ONLY if zero violations
        is_safe = (len(person_violations) == 0)
        status = "Safe" if is_safe else "Unsafe"

        # Determine issue type for visual styling
        has_helmet_violation = any(v["violation_type"] == "helmet" for v in person_violations)
        only_secondary = (not is_safe) and (not has_helmet_violation)

        person_data = {
            "id": idx + 1,
            "bbox": p_box,
            "confidence": p_conf,
            "status": status,
            "is_safe": is_safe,
            "only_secondary": only_secondary,  # Vest/Goggles-only issue -> amber
            "violations": person_violations,
            "matched_ppe": matched_ppe
        }

        evaluated_persons.append(person_data)
        all_violations.extend(person_violations)

    safe_count = sum(1 for p in evaluated_persons if p["is_safe"])
    unsafe_count = total_people - safe_count
    compliance_percent = round((safe_count / total_people) * 100.0, 1) if total_people > 0 else 0.0

    return {
        "total_people": total_people,
        "safe_count": safe_count,
        "unsafe_count": unsafe_count,
        "compliance_percent": compliance_percent,
        "persons": evaluated_persons,
        "violations": all_violations
    }
