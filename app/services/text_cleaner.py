"""
Text Cleaner & Normalizer for SafeSight AI - Milestone 2.
Cleans raw extracted document text, normalizes whitespace, removes repeated
header/footer patterns, repairs broken hyphenated linebreaks, and formats text.
"""
import re


def clean_text(text: str) -> str:
    """
    Normalizes whitespace and standardizes linebreaks.
    Preserves paragraph structure while stripping noisy artifacts and escape sequences.
    """
    if not text:
        return ""

    # Replace carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean escaped octal characters and escape sequences from PDF extractions
    text = re.sub(r'\\227', '—', text)
    text = re.sub(r'\\226', '–', text)
    text = re.sub(r'\\([()])', r'\1', text)
    text = re.sub(r'\\(\d+)', '', text)

    # Repair broken words from PDF extraction/OCR
    text = re.sub(r'Non-compli\s+ant', 'Non-compliant', text, flags=re.IGNORECASE)

    # Fix hyphenated words split across lines (e.g. "compli-\nance" -> "compliance")
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

    # Normalize multiple spaces and tabs into single space
    lines = []
    for line in text.split("\n"):
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        lines.append(cleaned_line)

    # Rejoin with standard newlines and reduce excessive blank lines
    joined = "\n".join(lines)
    joined = re.sub(r'\n{3,}', '\n\n', joined)

    return joined.strip()


def remove_repeated_headers_footers(page_texts: list) -> list:
    """
    Identifies and removes exact header or footer lines that repeat across pages.
    """
    if len(page_texts) <= 2:
        return [clean_text(t) for t in page_texts]

    # Count occurrences of the first 2 and last 2 non-empty lines on each page
    line_counts = {}
    for p_text in page_texts:
        lines = [l.strip() for l in p_text.split("\n") if l.strip()]
        candidates = []
        if len(lines) >= 1:
            candidates.append(lines[0])
        if len(lines) >= 2:
            candidates.append(lines[1])
        if len(lines) >= 3:
            candidates.append(lines[-1])
        if len(lines) >= 4:
            candidates.append(lines[-2])

        for c in set(candidates):
            line_counts[c] = line_counts.get(c, 0) + 1

    threshold = max(2, int(len(page_texts) * 0.7))
    boilerplate_lines = {l for l, count in line_counts.items() if count >= threshold}

    cleaned_pages = []
    for p_text in page_texts:
        lines = p_text.split("\n")
        filtered = [l for l in lines if l.strip() not in boilerplate_lines]
        cleaned_pages.append(clean_text("\n".join(filtered)))

    return cleaned_pages
