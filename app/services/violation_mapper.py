"""
SafeSight AI — Violation Mapping & Presentation Helper.
Provides pure mapping functions for:
1. Status model: 5 database statuses -> 3 UI statuses (Pending, Reviewed, Resolved).
2. Violation type normalization: raw codes -> human-readable labels and icon metadata.
3. Date & time formatting: timestamp -> clean split columns.
4. Pagination running S.No calculation across pages.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


# =============================================================================
# 1. STATUS MODEL MAPPING
# =============================================================================
# Database values: 'detected', 'pending review', 'confirmed', 'dismissed', 'resolved'
# UI categories:
#   Pending (Orange)        <- 'detected', 'pending review'
#   Reviewed (Berry/Magenta) <- 'confirmed', 'dismissed' (with 'Dismissed' badge/tooltip)
#   Resolved (Green/Mint)   <- 'resolved'

def map_status_to_ui(raw_status: Optional[str]) -> Dict[str, Any]:
    """
    Maps any database status string to its UI presentation properties.
    Adheres strictly to the Sunrise Garden palette (0 black, 0 blue).
    """
    raw = (raw_status or "detected").strip().lower()

    if raw in ("detected", "pending review", "pending"):
        return {
            "ui_status": "Pending",
            "raw_status": raw,
            "tone": "warning",
            "color": "#FF9F1C",
            "bg_color": "rgba(255, 159, 28, 0.14)",
            "text_color": "#8F4E00",
            "badge_class": "badge-status-pending",
            "is_dismissed": False,
            "tooltip": "Pending Review" if raw == "pending review" else "Newly Detected"
        }
    elif raw in ("confirmed", "dismissed", "reviewed"):
        is_dismissed = (raw == "dismissed")
        return {
            "ui_status": "Reviewed",
            "raw_status": raw,
            "tone": "berry",
            "color": "#B5179E",
            "bg_color": "rgba(181, 23, 158, 0.14)",
            "text_color": "#6A0D5D",
            "badge_class": "badge-status-reviewed",
            "is_dismissed": is_dismissed,
            "tooltip": "Dismissed (Reviewed)" if is_dismissed else "Confirmed (Reviewed)"
        }
    elif raw in ("resolved",):
        return {
            "ui_status": "Resolved",
            "raw_status": raw,
            "tone": "success",
            "color": "#22B573",
            "bg_color": "rgba(34, 181, 115, 0.14)",
            "text_color": "#115E3B",
            "badge_class": "badge-status-resolved",
            "is_dismissed": False,
            "tooltip": "Action Completed & Resolved"
        }
    else:
        # Fallback for unknown status
        return {
            "ui_status": "Pending",
            "raw_status": raw,
            "tone": "warning",
            "color": "#FF9F1C",
            "bg_color": "rgba(255, 159, 28, 0.14)",
            "text_color": "#8F4E00",
            "badge_class": "badge-status-pending",
            "is_dismissed": False,
            "tooltip": f"Status: {raw}"
        }


def map_ui_status_to_db(ui_status: Optional[str]) -> str:
    """
    Maps a user-selected UI status ('Pending', 'Reviewed', 'Resolved')
    to the target database status value to write.
    """
    s = (ui_status or "").strip().lower()
    if s == "pending":
        return "pending review"
    elif s == "reviewed":
        return "confirmed"
    elif s == "resolved":
        return "resolved"
    elif s in ("detected", "pending review", "confirmed", "dismissed"):
        return s
    return "pending review"


def get_db_statuses_for_ui_filter(status_filter: Optional[str]) -> Optional[List[str]]:
    """
    Translates an incoming status filter (UI or raw) into the list of
    underlying database status values to match.
    """
    if not status_filter or status_filter.lower() in ("all", ""):
        return None

    s = status_filter.strip().lower()
    if s == "pending":
        return ["detected", "pending review"]
    elif s == "reviewed":
        return ["confirmed", "dismissed"]
    elif s == "resolved":
        return ["resolved"]
    elif s in ("detected", "pending review", "confirmed", "dismissed"):
        return [s]
    return [s]


# =============================================================================
# 2. VIOLATION TYPE MAPPING
# =============================================================================

def map_violation_type(raw_type: Optional[str]) -> Dict[str, str]:
    """
    Maps raw violation codes into user-friendly names, icon types, and tones.
    - no helmet -> 'Missing Helmet'
    - no vest -> 'Missing Safety Vest'
    - several PPE items missing -> 'No Safety Equipment'
    - anything else (goggles, gloves, shoes, other...) -> 'Other Safety Violation'
    """
    code = (raw_type or "other").strip().lower()

    if code in ("helmet", "no helmet", "no_helmet", "missing helmet", "hardhat"):
        return {
            "label": "Missing Helmet",
            "raw_code": code,
            "icon": "helmet",
            "tone": "danger",
            "color": "#E53950",
            "bg": "rgba(229, 57, 80, 0.12)"
        }
    elif code in ("vest", "no vest", "no_vest", "missing vest", "safety vest"):
        return {
            "label": "Missing Safety Vest",
            "raw_code": code,
            "icon": "vest",
            "tone": "warning",
            "color": "#FF9F1C",
            "bg": "rgba(255, 159, 28, 0.12)"
        }
    elif code in ("equipment", "several ppe items missing", "no safety equipment", "no_equipment"):
        return {
            "label": "No Safety Equipment",
            "raw_code": code,
            "icon": "equipment",
            "tone": "danger",
            "color": "#E53950",
            "bg": "rgba(229, 57, 80, 0.16)"
        }
    else:
        return {
            "label": "Other Safety Violation",
            "raw_code": code,
            "icon": "other",
            "tone": "berry",
            "color": "#B5179E",
            "bg": "rgba(181, 23, 158, 0.12)"
        }


# =============================================================================
# 3. DATE & TIME FORMATTING
# =============================================================================

def split_datetime(dt_val: Optional[Any]) -> Tuple[str, str]:
    """
    Splits any timestamp value (datetime object or string) into:
    (formatted_date, formatted_time).
    Example: 2026-11-20 10:42:15 -> ('20 Nov 2026', '10:42:15 AM')
    """
    if not dt_val:
        return ("Not recorded", "Not recorded")

    dt = None
    if isinstance(dt_val, datetime):
        dt = dt_val
    elif isinstance(dt_val, str):
        cleaned = dt_val.strip()
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(cleaned, fmt)
                break
            except ValueError:
                continue

    if dt:
        date_str = dt.strftime("%d %b %Y")
        time_str = dt.strftime("%I:%M:%S %p")
        return (date_str, time_str)

    return ("Not recorded", "Not recorded")


# =============================================================================
# 4. RUNNING S.NO CALCULATION
# =============================================================================

def calculate_sno(page: int, page_size: int, index: int) -> int:
    """
    Calculates 1-based running serial number across pages.
    Page 1: 1..10
    Page 2: 11..20
    """
    safe_page = max(1, int(page or 1))
    safe_size = max(1, int(page_size or 10))
    safe_index = max(0, int(index or 0))
    return (safe_page - 1) * safe_size + safe_index + 1
