"""
BGE-M3 Embedding Module — src/features/embedding.py
"""

import numpy as np
import requests
import json
import sys
from pathlib import Path
from typing import List


from concurrent.futures import ThreadPoolExecutor

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "bge-m3"
BATCH_SIZE = 128
MAX_WORKERS = 8  # Concurrent requests to keep GPU saturated


def _embed_single(text: str) -> List[float]:
    """
    Call the Ollama embedding API for a single text string.
    Returns a list of floats (the embedding vector).
    """
    payload = {"model": EMBED_MODEL, "prompt": text}
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["embedding"]
    except requests.exceptions.ConnectionError:
        print("\n[Embedding] ERROR: Ollama is not running!")
        sys.exit(1)
    except Exception as e:
        # print(f"\n[Embedding] ERROR calling Ollama: {e}")
        return []


def embed_texts(texts: List[str], batch_size: int = BATCH_SIZE) -> np.ndarray:
    """
    Encode a list of text strings into a 2D embedding matrix using concurrency.
    """
    if not texts:
        return np.array([])

    total = len(texts)
    all_embeddings = [None] * total

    print(f"  [Embedding] Encoding {total:,} texts with {EMBED_MODEL}...")
    print(f"  [Embedding] GPU Optimization: Using {MAX_WORKERS} concurrent threads.")

    def process_item(idx: int):
        text = str(texts[idx])
        if not text or not text.strip():
            return [0.0] * 1024
        vec = _embed_single(text[:2048])
        return vec if vec else [0.0] * 1024

    from tqdm import tqdm

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Use tqdm for a beautiful, real-time progress bar
        with tqdm(total=total, desc=f"  [Embedding] {split_name if 'split_name' in locals() else ''}", unit="ticket") as pbar:
            for i in range(0, total, batch_size):
                chunk_indices = range(i, min(i + batch_size, total))
                results = list(executor.map(process_item, chunk_indices))
                
                for j, res in enumerate(results):
                    all_embeddings[i + j] = res
                
                pbar.update(len(results))

    print(f"\n  [Embedding] Done. Finalizing matrix...")
    matrix = np.array(all_embeddings, dtype=np.float32)
    return matrix


def check_ollama_running() -> bool:
    """Check if Ollama is running and BGE-M3 is available."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        has_bge = any("bge-m3" in m for m in models)
        if not has_bge:
            print(f"[Embedding] WARNING: bge-m3 not found. Available: {models}")
            print("[Embedding] Run: ollama pull bge-m3")
            return False
        return True
    except Exception:
        return False
