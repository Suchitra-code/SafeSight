"""
Unit test verifying no forbidden black or blue colors appear in the application (Milestone 5).
"""
import pytest
from tools.check_colors import hex_to_hsl, is_forbidden_hsl, check_all_colors

def test_checker_detects_forbidden_blue_and_black():
    """Verifies that check_colors correctly identifies forbidden colors."""
    # Pure black
    h, s, l = hex_to_hsl("#000000")
    forbidden, reason = is_forbidden_hsl(h, s, l)
    assert forbidden is True
    assert "lightness" in reason.lower()

    # Dark charcoal
    h, s, l = hex_to_hsl("#111111")
    forbidden, reason = is_forbidden_hsl(h, s, l)
    assert forbidden is True

    # Pure blue (#0000ff)
    h, s, l = hex_to_hsl("#0000ff")
    forbidden, reason = is_forbidden_hsl(h, s, l)
    assert forbidden is True
    assert "blue" in reason.lower()

    # Sky blue / cyan (#00bfff, #00ffff)
    h, s, l = hex_to_hsl("#00bfff")
    forbidden, reason = is_forbidden_hsl(h, s, l)
    assert forbidden is True

    # Allowed Sunrise Garden colors
    # Warm cream (#FFF7EE)
    h, s, l = hex_to_hsl("#FFF7EE")
    forbidden, _ = is_forbidden_hsl(h, s, l)
    assert forbidden is False

    # Coral (#FF6B4A)
    h, s, l = hex_to_hsl("#FF6B4A")
    forbidden, _ = is_forbidden_hsl(h, s, l)
    assert forbidden is False

    # Mint green (#22B573)
    h, s, l = hex_to_hsl("#22B573")
    forbidden, _ = is_forbidden_hsl(h, s, l)
    assert forbidden is False

    # Deep plum text (#4A1D2F) -> lightness ~20%, hue ~335 (magenta/red-purple)
    h, s, l = hex_to_hsl("#4A1D2F")
    forbidden, _ = is_forbidden_hsl(h, s, l)
    assert forbidden is False


def test_codebase_has_zero_forbidden_colors():
    """Verifies that the whole codebase scan yields 0 forbidden colors."""
    violations = check_all_colors()
    assert len(violations) == 0, f"Expected 0 violations, found {len(violations)}: {violations[:5]}"

