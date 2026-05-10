"""Semantic retrieval from ChromaDB — find similar historical tickets."""

import numpy as np
import ollama
from pathlib import Path
from src.vector.indexer import load_index
from app.config import settings

_collection = None


def _get_collection():
    """Lazy-load the ChromaDB collection."""
    global _collection
    if _collection is None:
        _collection = load_index()
    return _collection


def embed_text(text: str) -> list[float]:
    """Embed a single text string using BGE-M3 via Ollama (GPU-accelerated)."""
    # Sanitize: remove non-ASCII characters that cause Ollama JSON encoding errors
    clean_text = text.encode("ascii", errors="ignore").decode("ascii").strip()
    if not clean_text:
        clean_text = "empty"
    response = ollama.embed(
        model=settings.OLLAMA_EMBED_MODEL,
        input=clean_text
    )
    return response["embeddings"][0]


def retrieve_similar(
    query_text: str,
    top_k: int = 5,
    category_filter: str = None,
) -> list[dict]:
    """
    Find the top-K most semantically similar tickets to the query.
    Optionally filter by category for more focused retrieval.
    """
    col = _get_collection()
    query_embedding = embed_text(query_text)

    where_filter = None
    if category_filter:
        where_filter = {"category": {"$eq": category_filter}}

    results = col.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["metadatas", "distances"]
    )

    hits = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        hits.append({
            "ticket_id": results["ids"][0][i],
            "similarity": round(1.0 - distance, 4),
            "category": meta.get("category", ""),
            "priority": meta.get("priority", ""),
            "subject": meta.get("subject", ""),
        })

    return hits


def retrieve_by_embedding(
    embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Find similar tickets given a pre-computed embedding vector (fast path for pipeline)."""
    col = _get_collection()

    results = col.query(
        query_embeddings=[embedding],
        n_results=top_k,
        include=["metadatas", "distances"]
    )

    hits = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        distance = results["distances"][0][i]
        hits.append({
            "ticket_id": results["ids"][0][i],
            "similarity": round(1.0 - distance, 4),
            "category": meta.get("category", ""),
            "priority": meta.get("priority", ""),
            "subject": meta.get("subject", ""),
        })

    return hits
