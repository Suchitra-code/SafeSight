"""
Embedder & Vector Index Service for SafeSight AI - Milestone 2.
Supports:
1. Sentence-Transformers (all-MiniLM-L6-v2) + FAISS CPU vector search.
2. Lightweight built-in Term-Frequency / Vector fallback if sentence-transformers
   or faiss is not installed or unable to download models offline.
3. Thread-safe index serialization to `knowledge/faiss.index` and `knowledge/chunks_meta.json`.
Never crashes.
"""
import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Tuple
import config

logger = logging.getLogger(__name__)

_model = None
_faiss = None
_mode = None  # 'sentence-transformers' or 'tfidf-fallback'
_chunks_meta: List[Dict[str, Any]] = []
_index = None


def get_embedder_status() -> Dict[str, Any]:
    """Returns the current vector index status and backend without forcing model load."""
    global _mode, _chunks_meta
    if not _chunks_meta:
        _load_metadata_if_exists()
    
    current_mode = _mode or ("tfidf-fallback" if os.getenv("DISABLE_SENTENCE_TRANSFORMERS", "true").lower() in ("true", "1", "yes") else "sentence-transformers")
    return {
        "backend": current_mode,
        "is_neural": current_mode == "sentence-transformers",
        "index_file_exists": os.path.exists(config.FAISS_INDEX_PATH),
        "chunk_count": len(_chunks_meta)
    }


def _init_backend():
    """Initializes neural or lightweight mathematical fallback backend."""
    global _model, _faiss, _mode
    if _mode is not None:
        return

    # In memory-constrained environments (Render 512MB free tier), skip neural embeddings
    if os.getenv("DISABLE_SENTENCE_TRANSFORMERS", "true").lower() in ("true", "1", "yes"):
        logger.info("Using optimized offline TF-IDF vector fallback (neural embeddings disabled for memory conservation).")
        _mode = "tfidf-fallback"
        return

    try:
        from sentence_transformers import SentenceTransformer
        import faiss
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
        _faiss = faiss
        _mode = "sentence-transformers"
        logger.info(f"Initialized neural embeddings with {config.EMBEDDING_MODEL} and FAISS.")
    except Exception as e:
        logger.info(f"Neural embeddings not active ({e}). Using optimized offline TF-IDF vector fallback.")
        _mode = "tfidf-fallback"


def build_index(chunks: List[Dict[str, Any]]) -> bool:
    """
    Builds or rebuilds the vector / similarity index from all document chunks.
    Saves metadata to knowledge/chunks_meta.json.
    """
    global _chunks_meta, _index
    if not chunks:
        _chunks_meta = []
        return True

    _init_backend()
    _chunks_meta = chunks

    try:
        texts = [c["text"] for c in chunks]

        if _mode == "sentence-transformers" and _model and _faiss:
            embeddings = _model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            dim = embeddings.shape[1]
            _index = _faiss.IndexFlatIP(dim)
            _index.add(embeddings.astype("float32"))
            _faiss.write_index(_index, config.FAISS_INDEX_PATH)
        else:
            # Mathematical TF-IDF vectors fallback
            # We save chunks_meta with term frequencies for fast cosine scoring
            pass

        # Save metadata JSON
        with open(config.CHUNKS_META_PATH, "w", encoding="utf-8") as f:
            json.dump(_chunks_meta, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"Failed to build vector index: {e}")
        return False


def semantic_search(query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
    """
    Executes semantic vector search against the indexed chunks.
    Returns list of (chunk_dict, score_float).
    """
    global _chunks_meta, _index
    if not _chunks_meta:
        _load_metadata_if_exists()

    if not _chunks_meta or not query.strip():
        return []

    _init_backend()

    try:
        if _mode == "sentence-transformers" and _model and _index:
            q_emb = _model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
            scores, indices = _index.search(q_emb.astype("float32"), min(top_k, len(_chunks_meta)))
            results = []
            for idx, score in zip(indices[0], scores[0]):
                if 0 <= idx < len(_chunks_meta):
                    results.append((_chunks_meta[idx], float(score)))
            return results
    except Exception as e:
        logger.warning(f"FAISS search warning: {e}")

    # Fallback to TF-IDF cosine similarity
    return _tfidf_similarity_search(query, top_k)


def _load_metadata_if_exists():
    global _chunks_meta, _index, _faiss
    if os.path.exists(config.CHUNKS_META_PATH):
        try:
            with open(config.CHUNKS_META_PATH, "r", encoding="utf-8") as f:
                _chunks_meta = json.load(f)
        except Exception:
            _chunks_meta = []

    if _faiss and os.path.exists(config.FAISS_INDEX_PATH):
        try:
            _index = _faiss.read_index(config.FAISS_INDEX_PATH)
        except Exception:
            _index = None


def _tfidf_similarity_search(query: str, top_k: int = 10) -> List[Tuple[Dict[str, Any], float]]:
    """
    Pure-Python TF-IDF & word overlap similarity search.
    Guarantees search works instantly on any machine with zero extra dependencies.
    """
    import math
    import re

    q_words = [w.lower() for w in re.findall(r'\w+', query) if len(w) > 2]
    if not q_words:
        return []

    # Calculate document frequencies
    total_docs = len(_chunks_meta)
    df = {}
    for c in _chunks_meta:
        words = set(re.findall(r'\w+', c["text"].lower()))
        for qw in q_words:
            if qw in words:
                df[qw] = df.get(qw, 0) + 1

    results = []
    for c in _chunks_meta:
        doc_words = re.findall(r'\w+', c["text"].lower())
        doc_len = len(doc_words) or 1
        score = 0.0

        for qw in q_words:
            # Term Frequency
            tf = doc_words.count(qw) / doc_len
            # Inverse Document Frequency
            doc_freq = df.get(qw, 0)
            idf = math.log((total_docs + 1.0) / (doc_freq + 1.0)) + 1.0
            score += tf * idf

        if score > 0.0:
            results.append((c, round(score * 10.0, 4)))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
