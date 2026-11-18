"""
Inspection Report Extractor for SafeSight AI - Milestone 2.
Extracts:
1. Header fields: Report ID, Date, Site/Location, Area/Zone, Inspector Name,
   Supervisor Name, Company, Shift, Weather.
2. Findings: Description, Category, Severity (LOW, MEDIUM, HIGH, CRITICAL),
   Location, Corrective Action, Responsible Person, Due Date, Status (open, in progress, closed).
3. Summary stats: Total findings, counts by severity, compliance score.

Supports both table-style format and paragraph/bullet style format.
Dates parsed to YYYY-MM-DD via python-dateutil with fallbacks.
Scores confidence (0-1) and logs page numbers.
"""
import re
from typing import List, Dict, Any, Tuple
from dateutil import parser as date_parser


def parse_date_to_iso(date_str: str) -> str:
    """Parses arbitrary date string to YYYY-MM-DD; returns None on failure."""
    if not date_str:
        return None
    cleaned = date_str.strip().rstrip(".,;")
    try:
        dt = date_parser.parse(cleaned, fuzzy=True)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # Simple regex for DD/MM/YYYY or YYYY-MM-DD
        m = re.search(r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})', cleaned)
        if m:
            return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        m2 = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', cleaned)
        if m2:
            return f"{m2.group(3)}-{int(m2.group(2)):02d}-{int(m2.group(1)):02d}"
        return None


def extract_header_fields(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts standard inspection header metadata from document pages.
    """
    fields = []
    first_page_text = pages[0]["text"] if pages else ""
    first_two_pages = "\n".join(p["text"] for p in pages[:2])

    patterns = [
        ("report_id", r"(?:Report\s*(?:ID|No|Number|#)|Audit\s*(?:ID|No|#))\s*[:\-]?\s*([A-Za-z0-9\-_/]+)", 0.95),
        ("inspection_date", r"(?:Inspection\s*Date|Audit\s*Date|Date\s*of\s*Inspection|Date)\s*[:\-]?\s*([A-Za-z0-9\s,\-/\.]+?)(?=\n|$|\s{2,})", 0.90),
        ("site_location", r"(?:Site\s*Location|Location|Facility|Job\s*Site|Plant)\s*[:\-]?\s*([^\n;]{3,50})", 0.85),
        ("area_zone", r"(?:Area|Zone|Section|Work\s*Area)\s*[:\-]?\s*([^\n;]{2,50})", 0.85),
        ("inspector_name", r"(?:Inspector\s*(?:Name)?|Auditor\s*(?:Name)?|Inspected\s*By)\s*[:\-]?\s*([A-Za-z\.\s]{3,40})(?=\n|$|,|\s{2,})", 0.90),
        ("supervisor_name", r"(?:Supervisor\s*(?:Name)?|Site\s*Manager|Foreman)\s*[:\-]?\s*([A-Za-z\.\s]{3,40})(?=\n|$|,|\s{2,})", 0.85),
        ("company", r"(?:Company|Contractor|Organization)\s*[:\-]?\s*([^\n;]{3,50})", 0.80),
        ("shift", r"(?:Shift|Time\s*of\s*Day)\s*[:\-]?\s*(Day|Night|Evening|Morning|Shift\s*[A-C1-3])", 0.85),
        ("weather", r"(?:Weather|Conditions)\s*[:\-]?\s*([^\n;]{3,30})", 0.75),
    ]

    for field_name, regex, conf in patterns:
        m = re.search(regex, first_two_pages, re.IGNORECASE)
        val = None
        if m:
            raw_val = m.group(1).strip()
            if field_name == "inspection_date":
                val = parse_date_to_iso(raw_val) or raw_val
            else:
                val = raw_val

        fields.append({
            "field_name": field_name,
            "field_value": val if val else None,
            "confidence": conf if val else 0.0,
            "page_no": 1,
            "is_edited": False
        })

    return fields


def _classify_finding_category(text: str) -> str:
    """Categorizes finding text into PPE or safety violation categories."""
    t = text.lower()
    if any(k in t for k in ["helmet", "hard hat", "head protection"]):
        return "helmet"
    if any(k in t for k in ["vest", "hi-vis", "high visibility", "jacket"]):
        return "vest"
    if any(k in t for k in ["goggle", "glasses", "eye protection", "face shield"]):
        return "goggles"
    if any(k in t for k in ["glove", "hand protection"]):
        return "gloves"
    if any(k in t for k in ["boot", "shoe", "footwear", "toe"]):
        return "footwear"
    if any(k in t for k in ["fall", "harness", "lanyard", "scaffold", "working at height", "guardrail"]):
        return "fall protection"
    if any(k in t for k in ["electr", "wiring", "breaker", "cables", "socket"]):
        return "electrical"
    if any(k in t for k in ["housekeeping", "spill", "debris", "trip hazard", "clutter"]):
        return "housekeeping"
    if any(k in t for k in ["equipment", "forklift", "crane", "guard", "machinery"]):
        return "equipment"
    return "other"


def _classify_severity(text: str) -> str:
    """Detects severity from text cues."""
    t = text.lower()
    if any(k in t for k in ["critical", "fatal", "imminent", "danger", "stop work", "immediate danger"]):
        return "CRITICAL"
    if any(k in t for k in ["high", "severe", "serious", "major", "urgent"]):
        return "HIGH"
    if any(k in t for k in ["medium", "moderate", "warning"]):
        return "MEDIUM"
    return "LOW"


def extract_findings(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts individual findings from report pages (table or paragraph style).
    """
    findings = []

    for p in pages:
        page_no = p["page_no"]
        text = p["text"]
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Pattern 1: Table-style pipe/tab separated lines or finding rows
        # E.g. "F-01 | No Hardhat worn | High | Zone B | Issue warning | John | 2026-05-10 | Open"
        for line in lines:
            if "|" in line:
                parts = [part.strip() for part in line.split("|")]
                if len(parts) >= 3 and not any(h in parts[0].lower() for h in ["item", "finding", "description", "id", "#"]):
                    desc = parts[1] if len(parts) > 1 and len(parts[1]) > 5 else parts[0]
                    if len(desc) < 5 or desc.lower().startswith("finding no"):
                        continue

                    sev = "LOW"
                    for part in parts:
                        s_guess = _classify_severity(part)
                        if s_guess != "LOW":
                            sev = s_guess
                            break

                    loc = parts[3] if len(parts) > 3 else "On Site"
                    action = parts[4] if len(parts) > 4 else None
                    resp = parts[5] if len(parts) > 5 else None
                    due = parse_date_to_iso(parts[6]) if len(parts) > 6 else None
                    status = "open"
                    line_lower = line.lower()
                    if "closed" in line_lower or "resolved" in line_lower:
                        status = "closed"
                    elif "in progress" in line_lower:
                        status = "in progress"

                    findings.append({
                        "description": desc,
                        "category": _classify_finding_category(line),
                        "severity": sev,
                        "location": loc,
                        "corrective_action": action,
                        "responsible_person": resp,
                        "due_date": due,
                        "status": status,
                        "confidence": 0.90,
                        "page_no": page_no
                    })

        # Pattern 2: Tabular/Flattened findings with IDs (e.g., F-014-01, F-01, Finding 1)
        # Matches patterns where a table was serialized into continuous text without pipe characters
        id_tokens = list(re.finditer(r'\b(F-\d+-\d+|F-\d+|Finding\s*\d+|DEF-\d+)\b', text, re.IGNORECASE))
        for i, tm in enumerate(id_tokens):
            f_id = tm.group(0).strip()
            start_pos = tm.end()
            # Stop at the next finding ID or a section boundary like "3. Personal Protective Equipment"
            raw_end = id_tokens[i + 1].start() if i + 1 < len(id_tokens) else len(text)
            body = text[start_pos:raw_end].strip()

            # Check if there is a major numbered heading ending this body
            head_m = re.search(r'\n\s*\d+\.\s+[A-Z]|\b\d+\.\s+[A-Z][a-z]+', body)
            if head_m:
                body = body[:head_m.start()].strip()

            # Try to parse components: Desc, Severity, Action, Due Date, Status
            parsed_m = re.search(
                r'^(.*?)\s+(High|Medium|Low|Critical)\s+(.*?)\s+(\d{1,2}\s+[A-Za-z]{3,}\s+\d{4}|\d{4}-\d{2}-\d{2})\s+(Open|Closed|In\s+progress)',
                body, re.IGNORECASE | re.DOTALL
            )
            if parsed_m:
                desc = parsed_m.group(1).strip()
                sev = parsed_m.group(2).upper()
                action = parsed_m.group(3).strip()
                due = parse_date_to_iso(parsed_m.group(4))
                status = parsed_m.group(5).lower()
                cat = _classify_finding_category(desc)
                findings.append({
                    "description": f"{f_id}: {desc}",
                    "category": cat,
                    "severity": sev,
                    "location": "Fabrication Zone",
                    "corrective_action": action,
                    "responsible_person": None,
                    "due_date": due,
                    "status": status,
                    "confidence": 0.92,
                    "page_no": page_no
                })
            else:
                # Fallback if structure varies slightly
                sev = _classify_severity(body)
                cat = _classify_finding_category(body)
                findings.append({
                    "description": f"{f_id}: {body[:140]}",
                    "category": cat,
                    "severity": sev,
                    "location": "Site Area",
                    "corrective_action": None,
                    "responsible_person": None,
                    "due_date": None,
                    "status": "open",
                    "confidence": 0.80,
                    "page_no": page_no
                })

        # Pattern 3: Paragraph / numbered findings
        # E.g. "Finding 1: Worker observed operating without safety vest in Zone A."
        para_matches = re.finditer(
            r'(?:Finding|Observation|Deficiency|Item)\s*(?:#|\d+)?\s*[:\-]\s*(.*?)(?=(?:Finding|Observation|Deficiency|Item)\s*(?:#|\d+)?\s*[:\-]|\n\s*\n|$)',
            text, re.DOTALL | re.IGNORECASE
        )
        for m in para_matches:
            block = m.group(1).strip()
            if len(block) > 15:
                # Avoid duplicate table captures
                if any(f["description"] in block for f in findings if f["page_no"] == page_no):
                    continue

                desc = block.split("\n")[0]
                sev = _classify_severity(block)
                cat = _classify_finding_category(block)

                # Corrective action
                act_m = re.search(r'(?:Action|Corrective Action|Remedy)\s*[:\-]\s*([^\n.]+)', block, re.IGNORECASE)
                action = act_m.group(1).strip() if act_m else None

                # Due date
                due_m = re.search(r'(?:Due|Target Date|Due Date)\s*[:\-]\s*([^\n;]+)', block, re.IGNORECASE)
                due = parse_date_to_iso(due_m.group(1)) if due_m else None

                # Status
                st = "open"
                if "closed" in block.lower():
                    st = "closed"
                elif "in progress" in block.lower():
                    st = "in progress"

                findings.append({
                    "description": desc,
                    "category": cat,
                    "severity": sev,
                    "location": "Site Area",
                    "corrective_action": action,
                    "responsible_person": None,
                    "due_date": due,
                    "status": st,
                    "confidence": 0.85,
                    "page_no": page_no
                })

    return findings


def extract_report_data(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Full extraction orchestrator for an inspection report.
    Returns {fields, findings, summary}.
    """
    fields = extract_header_fields(pages)
    findings = extract_findings(pages)

    # Compute summary numbers
    sev_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    cat_counts = {}
    open_count = 0
    closed_count = 0

    for f in findings:
        sev = f["severity"]
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
        cat = f["category"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if f["status"] == "closed":
            closed_count += 1
        else:
            open_count += 1

    total = len(findings)
    # Estimate compliance score if report found; baseline 100 - (critical*20 + high*10 + med*5)
    compliance_score = max(40.0, round(100.0 - (sev_counts["CRITICAL"] * 20 + sev_counts["HIGH"] * 10 + sev_counts["MEDIUM"] * 5), 1))

    return {
        "fields": fields,
        "findings": findings,
        "summary": {
            "total_findings": total,
            "severity_counts": sev_counts,
            "category_counts": cat_counts,
            "open_count": open_count,
            "closed_count": closed_count,
            "compliance_score": compliance_score
        }
    }
