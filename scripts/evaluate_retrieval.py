"""
Evaluate semantic retrieval quality using pre-computed embeddings.
No LLM calls. No re-embedding. Pure vector math — completes in seconds.
"""

import numpy as np
import pandas as pd
import time
from pathlib import Path
from collections import defaultdict
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.vector.indexer import load_index

GOLD_DIR = Path("data/gold")
SAMPLE_SIZE = 200
TOP_K = 5


def evaluate_retrieval():
    print("=" * 60)
    print("  SupportPulse - Phase 4: Vector Retrieval Evaluation")
    print(f"  Method: Pre-computed BGE-M3 embeddings (no re-embedding)")
    print(f"  Sample : {SAMPLE_SIZE} queries | Top-K: {TOP_K}")
    print("=" * 60)

    col = load_index()
    print(f"  [Eval] Collection loaded: {col.count():,} vectors")

    # Load test set (pre-computed embeddings + ground truth labels)
    test_embs = np.load(GOLD_DIR / "test_embeddings.npy")
    test_df = pd.read_parquet(GOLD_DIR / "test.parquet")

    # Sample query indices
    rng = np.random.default_rng(42)
    sample_idx = rng.choice(len(test_df), size=SAMPLE_SIZE, replace=False)

    category_match_counts = defaultdict(lambda: {"hits": 0, "total": 0})
    total_matches = 0
    latencies = []

    print(f"\n  [Eval] Running {SAMPLE_SIZE} queries...", flush=True)
    for i, idx in enumerate(sample_idx):
        query_emb = test_embs[idx].tolist()
        true_cat = str(test_df.iloc[idx]["category"]).lower().strip()

        t0 = time.time()
        results = col.query(
            query_embeddings=[query_emb],
            n_results=TOP_K,
            include=["metadatas", "distances"]
        )
        latencies.append((time.time() - t0) * 1000)

        retrieved_cats = [
            m.get("category", "").lower().strip()
            for m in results["metadatas"][0]
        ]

        # Precision@K — how many of top-K match the true category
        matches = sum(1 for cat in retrieved_cats if cat == true_cat)
        category_match_counts[true_cat]["hits"] += matches
        category_match_counts[true_cat]["total"] += TOP_K

        if matches > 0:
            total_matches += 1

        if (i + 1) % 50 == 0:
            pct = ((i + 1) / SAMPLE_SIZE) * 100
            print(f"  [Eval] {pct:.0f}% ({i+1}/{SAMPLE_SIZE})", flush=True)

    # Metrics
    recall_at_k = total_matches / SAMPLE_SIZE
    avg_latency = sum(latencies) / len(latencies)
    p99_latency = sorted(latencies)[int(0.99 * len(latencies))]

    print("\n" + "=" * 60)
    print(f"  RETRIEVAL EVALUATION RESULTS")
    print("=" * 60)
    print(f"  Recall@{TOP_K}  : {recall_at_k:.4f}  ({total_matches}/{SAMPLE_SIZE} queries found match)")
    print(f"  Avg Latency : {avg_latency:.2f}ms per query")
    print(f"  P99 Latency : {p99_latency:.2f}ms per query")
    print()
    print(f"  Per-Category Precision@{TOP_K}:")
    for cat, counts in sorted(category_match_counts.items()):
        precision = counts["hits"] / counts["total"] if counts["total"] > 0 else 0
        n_queries = counts["total"] // TOP_K
        bar_len = int(precision * 20)
        bar = "#" * bar_len + "-" * (20 - bar_len)
        print(f"    {cat:<15} [{bar}] {precision:.2f} (n={n_queries})")
    print("=" * 60)

    return {
        "recall_at_k": recall_at_k,
        "avg_latency_ms": avg_latency,
        "p99_latency_ms": p99_latency,
    }


if __name__ == "__main__":
    evaluate_retrieval()
