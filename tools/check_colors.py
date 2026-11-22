"""
tools/check_colors.py — Strict Automated Color System Checker (Milestone 5)

Rule:
- FORBIDDEN:
  1. Black or near-black: Lightness < 18% (e.g. #000, #111, #222, etc.)
  2. Blue family: Hue between 175° and 275° with Saturation > 12% (blue, navy, cyan, teal, indigo, sky blue, etc.)
  3. Specific named colors: black, blue, navy, darkblue, midnightblue, royalblue,
     steelblue, dodgerblue, cornflowerblue, slateblue, cyan, teal, indigo, slategray, darkslategray.
- ALLOWED:
  1. Palette values defined in static/css/theme.css
  2. Pure white (#fff, #ffffff, rgb(255,255,255)), transparent, rgba(..., 0), var(--*)
"""

import os
import re
import sys
import colorsys
from typing import List, Tuple, Dict, Any

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FORBIDDEN_NAMES = {
    "black", "blue", "navy", "darkblue", "midnightblue", "royalblue",
    "steelblue", "dodgerblue", "cornflowerblue", "slateblue", "cyan",
    "teal", "indigo", "slategray", "darkslategray"
}

# Explicit allowed hex colors from the Sunrise Garden palette + tints
ALLOWED_HEX = {
    "#fff", "#ffffff", "#fff7ee", "#ffeaf2", "#ffe3d3", "#ddf7e8",
    "#fff1b8", "#f8ddf0", "#ff6b4a", "#ff9f1c", "#ffc93c", "#8cc63f",
    "#22b573", "#ff4d8d", "#d6247f", "#b5179e", "#e53950", "#4a1d2f",
    "#6b3a4d", "#9a6b7e", "#f3d9cf", "#e8c4b8", "#c07000", "#ffe2e6",
    "#fce0ef", "#fffdf9", "#fff4ee", "#fefefe", "#fafafa",
    # Section 2 Pastel & Accent system
    "#fff0df", "#f0a45d", "#8a4f14",  # Peach
    "#ffe8f0", "#e76b9a", "#8f2f57",  # Pink
    "#ddf7ea", "#35b982", "#10603f",  # Mint
    "#f8e3f4", "#c94bb5", "#7a2570",  # Orchid
    "#ffe5de", "#f07861", "#8f3425",  # Coral
    "#fff4c2", "#f2b705", "#6b4b00",  # Sun
    "#eaf6d2", "#8cc63f", "#445e14",  # Lime
    "#ffe1e4", "#e53950", "#9b1c2e",  # Red
    "#fff9f2", "#7a5563", "#f3ddd3",  # Neutrals (Cream, Muted plum, Borders)
    "#d85338", "#1e9462"              # High-contrast accessible button darkeners
}

def hex_to_hsl(hex_str: str) -> Tuple[float, float, float]:
    """Convert hex string (#rgb or #rrggbb) to HSL (h: 0-360, s: 0-100, l: 0-100)."""
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 8: # rgba hex
        h = h[:6]
    if len(h) != 6:
        return (0.0, 0.0, 50.0)
    
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0

    h_val, l_val, s_val = colorsys.rgb_to_hls(r, g, b)
    return (h_val * 360.0, s_val * 100.0, l_val * 100.0)

def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    h_val, l_val, s_val = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    return (h_val * 360.0, s_val * 100.0, l_val * 100.0)

def is_forbidden_hsl(h: float, s: float, l: float, mode: str = "mentor_safe") -> Tuple[bool, str]:
    """Checks if HSL color violates Section 3.2 rules."""
    # Near black check: Lightness < 18% (forbidden in both modes)
    if l < 18.0:
        return True, f"Too dark/near-black: lightness {l:.1f}% < 18%"
    
    # In mentor_safe mode: Blue/teal/cyan family forbidden
    if mode == "mentor_safe":
        if 175.0 <= h <= 275.0 and s > 12.0:
            return True, f"Blue/teal/cyan family: hue {h:.1f}° in [175°, 275°], saturation {s:.1f}% > 12%"
    
    return False, ""

def scan_file_for_colors(file_path: str, mode: str = "mentor_safe") -> List[Dict[str, Any]]:
    """Scans a file line by line for forbidden colors."""
    violations = []
    
    # Skip vendor assets, database dumps, virtualenv, git, binary files
    rel_path = os.path.relpath(file_path, ROOT_DIR).replace("\\", "/")
    if any(p in rel_path for p in ["vendor/", ".git/", "venv/", "node_modules/", ".pytest_cache/", "__pycache__/", "site_map.json"]):
        return violations

    # In mentor_safe mode, vivid-specific stylesheet is inactive on the client
    if mode == "mentor_safe" and "vivid.css" in rel_path:
        return violations

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return violations

    # Strip multi-line comments for CSS/JS
    # Replace contents of /* ... */ with spaces to preserve line numbers
    def replace_comment(match):
        return "\n" * match.group(0).count("\n")
    
    content_no_comments = re.sub(r'/\*.*?\*/', replace_comment, content, flags=re.DOTALL)
    lines = content_no_comments.splitlines()

    for line_idx, line in enumerate(lines, 1):
        line_clean = line.strip()
        # Skip single-line comments
        if line_clean.startswith("//") or line_clean.startswith("#") or line_clean.startswith("<!--"):
            continue

        # Strip inline // or # comments
        code_part = re.split(r'//|#(?![0-9a-fA-F])', line)[0]

        # 1. Check HEX colors (ignore HTML character entities like &#039;)
        hex_matches = re.findall(r'(?<!&)(#(?:[0-9a-fA-F]{3,4}){1,2})\b', line)
        for hex_code in hex_matches:
            hex_lower = hex_code.lower()
            if hex_lower in ALLOWED_HEX:
                continue
            h, s, l = hex_to_hsl(hex_lower)
            forbidden, reason = is_forbidden_hsl(h, s, l, mode=mode)
            if forbidden:
                violations.append({
                    "file": rel_path,
                    "line": line_idx,
                    "color": hex_code,
                    "reason": reason,
                    "snippet": line_clean[:80]
                })

        # 2. Check RGB / RGBA
        rgb_matches = re.findall(r'rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([\d\.]+))?\s*\)', line)
        for r_s, g_s, b_s, a_s in rgb_matches:
            if a_s and float(a_s) == 0:
                continue # fully transparent is allowed
            r, g, b = int(r_s), int(g_s), int(b_s)
            h, s, l = rgb_to_hsl(r, g, b)
            forbidden, reason = is_forbidden_hsl(h, s, l, mode=mode)
            if forbidden:
                violations.append({
                    "file": rel_path,
                    "line": line_idx,
                    "color": f"rgb({r},{g},{b})",
                    "reason": reason,
                    "snippet": line_clean[:80]
                })

        # 3. Check forbidden named colors (as CSS values)
        if mode == "mentor_safe":
            for name in FORBIDDEN_NAMES:
                pattern = rf'(?:[:,\s(])\b{name}\b(?:[;\s,)!]|$)'
                if re.search(pattern, line, re.IGNORECASE):
                    if f"--{name}" in line or f".{name}" in line:
                        continue
                    violations.append({
                        "file": rel_path,
                        "line": line_idx,
                        "color": name,
                        "reason": f"Explicit forbidden CSS named color '{name}'",
                        "snippet": line_clean[:80]
                    })
        else:
            # In vivid mode, only pure black is forbidden
            for name in ["black"]:
                pattern = rf'(?:[:,\s(])\b{name}\b(?:[;\s,)!]|$)'
                if re.search(pattern, line, re.IGNORECASE):
                    if f"--{name}" in line or f".{name}" in line:
                        continue
                    violations.append({
                        "file": rel_path,
                        "line": line_idx,
                        "color": name,
                        "reason": f"Explicit forbidden CSS named color '{name}'",
                        "snippet": line_clean[:80]
                    })

    return violations

def check_all_colors(dirs_to_scan: List[str] = None, mode: str = "mentor_safe") -> List[Dict[str, Any]]:
    if dirs_to_scan is None:
        dirs_to_scan = [
            os.path.join(ROOT_DIR, "app", "static"),
            os.path.join(ROOT_DIR, "app", "templates")
        ]
    
    all_violations = []
    for d in dirs_to_scan:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in [".css", ".html", ".js", ".svg"]:
                    full_p = os.path.join(root, file)
                    all_violations.extend(scan_file_for_colors(full_p, mode=mode))
                    
    return all_violations

if __name__ == "__main__":
    mode = "mentor_safe"
    for arg in sys.argv[1:]:
        if arg.startswith("--mode="):
            mode = arg.split("=", 1)[1].lower().strip()
        elif arg in ["vivid", "mentor_safe"]:
            mode = arg

    print("=" * 80)
    print(f"       SAFESIGHT AI - COLOR SYSTEM CHECKER (MODE: {mode.upper()})")
    print("=" * 80)
    violations = check_all_colors(mode=mode)
    if not violations:
        print(f"\nSUCCESS: 0 forbidden colors found in {mode.upper()} mode!\n")
        sys.exit(0)
    else:
        print(f"\nFOUND {len(violations)} COLOR VIOLATIONS ({mode.upper()} MODE):\n")
        print(f"{'File':<35} | {'Line':<5} | {'Color':<12} | {'Reason'}")
        print("-" * 80)
        for v in violations[:30]:
            print(f"{v['file']:<35} | {v['line']:<5} | {v['color']:<12} | {v['reason']}")
        if len(violations) > 30:
            print(f"... and {len(violations) - 30} more violations.")
        sys.exit(1)
