"""
WCAG 2.1 Contrast Ratio Verification Tool for SafeSight AI.
Ensures every text/background pair adheres to WCAG AA:
- Body text: >= 4.5:1
- Large / bold text or UI component badges: >= 3.0:1
"""
import sys

def hex_to_rgb(hex_code):
    hex_code = hex_code.strip().lstrip('#')
    if len(hex_code) == 3:
        hex_code = ''.join([c*2 for c in hex_code])
    return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

def relative_luminance(rgb):
    srgb = [c / 255.0 for c in rgb]
    lum = []
    for c in srgb:
        if c <= 0.03928:
            lum.append(c / 12.92)
        else:
            lum.append(((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * lum[0] + 0.7152 * lum[1] + 0.0722 * lum[2]

def contrast_ratio(hex1, hex2):
    lum1 = relative_luminance(hex_to_rgb(hex1))
    lum2 = relative_luminance(hex_to_rgb(hex2))
    l_light = max(lum1, lum2)
    l_dark = min(lum1, lum2)
    return (l_light + 0.05) / (l_dark + 0.05)

# Primary color pairs defined in SafeSight AI Sunrise Garden design system
PAIRS_TO_CHECK = [
    # 8-Tint Pastel System Text on Pastel Backgrounds (Body text >= 4.5:1)
    ("Peach text on pastel", "#8A4F14", "#FFF0DF", 4.5, "Peach card body text on pastel peach"),
    ("Pink text on pastel", "#8F2F57", "#FFE8F0", 4.5, "Pink card body text on pastel pink"),
    ("Mint text on pastel", "#10603F", "#DDF7EA", 4.5, "Mint card body text on pastel mint"),
    ("Orchid text on pastel", "#7A2570", "#F8E3F4", 4.5, "Orchid card body text on pastel orchid"),
    ("Coral text on pastel", "#8F3425", "#FFE5DE", 4.5, "Coral card body text on pastel coral"),
    ("Sun text on pastel", "#6B4B00", "#FFF4C2", 4.5, "Sun card body text on pastel sun"),
    ("Lime text on pastel", "#445E14", "#EAF6D2", 4.5, "Lime card body text on pastel lime"),
    ("Red text on pastel", "#9B1C2E", "#FFE1E4", 4.5, "Red card body text on pastel red"),

    # Neutral Surface Text (Body text >= 4.5:1)
    ("Primary text on card", "#4A1D2F", "#FFFFFF", 4.5, "Deep plum body text on white card surface"),
    ("Primary text on page", "#4A1D2F", "#FFF9F2", 4.5, "Deep plum body text on warm cream page background"),
    ("Secondary text on card", "#7A5563", "#FFFFFF", 4.5, "Muted plum body text on white card surface"),
    ("Secondary text on page", "#7A5563", "#FFF9F2", 4.5, "Muted plum body text on warm cream page background"),

    # Button & Badge Pairs (Large / UI badges >= 3.0:1 or >= 4.5:1)
    ("Deep Plum on Sun", "#4A1D2F", "#F2B705", 4.5, "Deep plum text on Sun accent badge"),
    ("White on Deep Red", "#FFFFFF", "#E53950", 3.0, "White text on Red critical badge / button"),
    ("White on Deep Orchid", "#FFFFFF", "#C94BB5", 3.0, "White text on Orchid button / badge"),
    ("Deep Plum on Mint Accent", "#4A1D2F", "#35B982", 4.5, "Deep plum text on Mint accent badge"),
    ("Deep Plum on Coral Accent", "#4A1D2F", "#F07861", 4.5, "Deep plum text on Coral accent badge"),
    ("White on Primary Coral Btn", "#FFFFFF", "#D85338", 3.0, "White text on accessible dark coral button"),
    ("White on Success Mint Btn", "#FFFFFF", "#1E9462", 3.0, "White text on accessible dark mint button"),
]

def run_contrast_check():
    print("=" * 80)
    print("       SAFESIGHT AI - WCAG 2.1 AA CONTRAST RATIO AUDIT")
    print("=" * 80)
    print(f"{'Pair Name':<28} | {'FG':<7} | {'BG':<7} | {'Ratio':<7} | {'Req':<5} | {'Result'}")
    print("-" * 80)
    
    all_passed = True
    for name, fg, bg, min_req, desc in PAIRS_TO_CHECK:
        ratio = contrast_ratio(fg, bg)
        passed = ratio >= min_req
        if not passed:
            all_passed = False
        status_str = "PASS" if passed else f"FAIL (<{min_req}:1)"
        print(f"{name:<28} | {fg:<7} | {bg:<7} | {ratio:>5.2f}:1 | {min_req:>3.1f}:1 | [{status_str}]")
        
    print("=" * 80)
    if all_passed:
        print("SUCCESS: All color pairs satisfy WCAG 2.1 AA contrast requirements!\n")
    else:
        print("WARNING: Some color pairs failed WCAG 2.1 AA contrast requirements!\n")
    return all_passed

if __name__ == "__main__":
    success = run_contrast_check()
    sys.exit(0 if success else 1)
