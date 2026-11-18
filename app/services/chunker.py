"""
Document Chunker for SafeSight AI - Milestone 2.
Splits document pages into searchable chunks of 200-300 words with ~40 words overlap.
Never cuts in the middle of a sentence.
Preserves page numbers, document IDs, repository IDs, and section context.
"""
import re
from typing import List, Dict, Any


def chunk_document(
    document_id: int,
    repository_id: int,
    pages: List[Dict[str, Any]],
    target_words: int = 250,
    overlap_words: int = 40
) -> List[Dict[str, Any]]:
    """
    Chunks a list of pages into coherent paragraph/sentence-bounded chunks.
    """
    chunks = []
    chunk_index = 0

    for p in pages:
        page_no = p.get("page_no", 1)
        text = p.get("text", "").strip()
        if not text:
            continue

        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        current_words = []
        current_sentences = []

        for s in sentences:
            words = s.split()
            current_sentences.append(s)
            current_words.extend(words)

            if len(current_words) >= target_words:
                chunk_text = " ".join(current_sentences)
                chunks.append({
                    "document_id": document_id,
                    "repository_id": repository_id,
                    "section_id": None,
                    "page_no": page_no,
                    "chunk_index": chunk_index,
                    "text": chunk_text
                })
                chunk_index += 1

                # Calculate overlap sentences
                overlap_count = 0
                keep_sentences = []
                for sent in reversed(current_sentences):
                    sent_words = sent.split()
                    if overlap_count + len(sent_words) <= overlap_words:
                        keep_sentences.insert(0, sent)
                        overlap_count += len(sent_words)
                    else:
                        break

                current_sentences = keep_sentences
                current_words = [w for sent in current_sentences for w in sent.split()]

        # Remainder chunk on this page
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunks.append({
                "document_id": document_id,
                "repository_id": repository_id,
                "section_id": None,
                "page_no": page_no,
                "chunk_index": chunk_index,
                "text": chunk_text
            })
            chunk_index += 1

    return chunks
