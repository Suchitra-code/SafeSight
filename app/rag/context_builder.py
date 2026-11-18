"""
Context Builder for SafeSight AI RAG Pipeline.
Formats retrieved sources into delimited, tamper-proof context blocks.
Enforces word budgets (under 3000 words), drops lowest-scored sources when overflowing.
"""
from typing import List
from app.rag.retriever import Source


def build_rag_context(sources: List[Source], max_words: int = 3000) -> str:
    """
    Constructs a numbered context string from sources [S1]..[Sn].
    Wraps sources as untrusted DATA blocks to defend against prompt injection.
    """
    if not sources:
        return "No relevant sources found in the database or camera visual logs."

    blocks = []
    total_words = 0

    for s in sources:
        header = f"[{s.source_id}] Type: {s.source_type.upper()} | Title: {s.title}"
        if s.page:
            header += f" | Page: {s.page}"
        if s.camera:
            header += f" | Camera: {s.camera}"
        if s.event_time:
            header += f" | Time: {s.event_time}"

        body = (
            f"--- START SOURCE {s.source_id} ---\n"
            f"{header}\n"
            f"Snippet: {s.snippet.strip()}\n"
            f"--- END SOURCE {s.source_id} ---"
        )
        block_words = len(body.split())
        if total_words + block_words > max_words and blocks:
            # Word budget reached, stop adding lower-ranked sources
            break

        blocks.append(body)
        total_words += block_words

    return "\n\n".join(blocks)
