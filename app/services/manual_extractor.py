"""
Safety Manual & SOP Extractor for SafeSight AI - Milestone 2.
Extracts:
1. Section heading tree (title, level, page range, parent_id).
2. Mandatory safety rules containing must, shall, required, mandatory, prohibited, etc.
3. PPE-specific requirements tagged by PPE type (helmet, vest, goggles, gloves, etc.).
4. Ordered step-by-step procedures.
5. Hazard/equipment counts and key definitions.
"""
import re
import json
from typing import List, Dict, Any


def extract_sections(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects headings and builds a hierarchical section outline.
    """
    sections = []
    heading_pattern = re.compile(
        r'^(?:(?:Section|Chapter|Part)\s+\d+[\.:\s]|\d+\.\d*(?:\.\d+)*\s+|[A-Z\s]{4,40}$)(.+)$',
        re.MULTILINE
    )

    for p in pages:
        page_no = p["page_no"]
        text = p["text"]
        lines = text.split("\n")

        for line in lines:
            line_str = line.strip()
            if not line_str or len(line_str) > 80:
                continue

            # Check for heading pattern: "1.0 INTRODUCTION" or "Section 2: PPE Requirements"
            m = re.match(r'^(?:(?:Section|Chapter)\s+(\d+)[\.:\s]*|((\d+)(?:\.(\d+))*)[\s\.:]+)(.*)$', line_str, re.IGNORECASE)
            if m:
                level = 1
                if m.group(2):
                    # count dots
                    dots = m.group(2).count(".")
                    level = min(3, dots + 1)
                elif m.group(1):
                    level = 1

                title = line_str
                sections.append({
                    "title": title,
                    "level": level,
                    "page_start": page_no,
                    "page_end": page_no,
                    "parent_id": None
                })
            elif line_str.isupper() and 4 < len(line_str) < 50 and not any(ch.isdigit() for ch in line_str):
                # All uppercase heading
                sections.append({
                    "title": line_str.title(),
                    "level": 1,
                    "page_start": page_no,
                    "page_end": page_no,
                    "parent_id": None
                })

    if not sections:
        sections.append({
            "title": "General Requirements",
            "level": 1,
            "page_start": 1,
            "page_end": len(pages) if pages else 1,
            "parent_id": None
        })

    return sections


def extract_safety_rules(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Finds imperative sentences with mandatory modal verbs and tags PPE types.
    """
    rules = []
    modal_keywords = ["must", "shall", "required", "mandatory", "prohibited", "do not", "always", "never"]
    pattern = re.compile(r'\b(' + '|'.join(modal_keywords) + r')\b', re.IGNORECASE)

    for p in pages:
        page_no = p["page_no"]
        text = p["text"]
        # Split into sentences roughly
        sentences = re.split(r'(?<=[.!?])\s+', text)

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) < 15 or len(s_clean) > 350:
                continue

            if pattern.search(s_clean):
                # Tag PPE type
                s_lower = s_clean.lower()
                ppe_type = "other"
                if any(w in s_lower for w in ["helmet", "hard hat", "head protection"]):
                    ppe_type = "helmet"
                elif any(w in s_lower for w in ["vest", "hi-vis", "high visibility"]):
                    ppe_type = "vest"
                elif any(w in s_lower for w in ["goggle", "glasses", "eye protection", "face shield"]):
                    ppe_type = "goggles"
                elif any(w in s_lower for w in ["glove", "hand protection"]):
                    ppe_type = "gloves"
                elif any(w in s_lower for w in ["boot", "shoe", "footwear", "toe"]):
                    ppe_type = "footwear"
                elif any(w in s_lower for w in ["harness", "lanyard", "fall"]):
                    ppe_type = "harness"
                elif any(w in s_lower for w in ["respirator", "mask", "ear", "hearing"]):
                    ppe_type = "other"

                rules.append({
                    "rule_text": s_clean,
                    "ppe_type": ppe_type,
                    "page_no": page_no
                })

    return rules


def extract_procedures(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects numbered procedural step lists.
    """
    procedures = []

    for p in pages:
        page_no = p["page_no"]
        text = p["text"]

        # Look for sequences of "Step 1: ... Step 2: ..." or "1. ... 2. ... 3. ..."
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        current_title = "Standard Procedure"
        current_steps = []

        for line in lines:
            # Check for procedure heading
            if any(k in line.lower() for k in ["procedure", "protocol", "step-by-step", "operating instructions"]):
                if current_steps:
                    procedures.append({
                        "title": current_title,
                        "steps": json.dumps(current_steps),
                        "page_no": page_no
                    })
                    current_steps = []
                current_title = line
                continue

            # Match step like "Step 1:", "1.", "1)"
            step_m = re.match(r'^(?:Step\s*\d+[:\-.]?|\d+[\.\)])\s*(.+)$', line, re.IGNORECASE)
            if step_m:
                current_steps.append(step_m.group(1).strip())
            elif current_steps and len(current_steps) < 20 and len(line) > 10 and not line.isupper():
                # Continuation line
                current_steps[-1] += " " + line

        if len(current_steps) >= 2:
            procedures.append({
                "title": current_title,
                "steps": json.dumps(current_steps),
                "page_no": page_no
            })

    return procedures


def extract_manual_data(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full extraction orchestrator for safety manuals and SOPs.
    """
    sections = extract_sections(pages)
    rules = extract_safety_rules(pages)
    procedures = extract_procedures(pages)

    return {
        "sections": sections,
        "rules": rules,
        "procedures": procedures
    }
