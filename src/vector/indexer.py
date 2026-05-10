"""Build and manage the ChromaDB vector index from pre-computed Phase 2 embeddings."""

import numpy as np
import pandas as pd
import chromadb
import time
from pathlib import Path

GOLD_DIR = Path("data/gold")
CHROMA_DIR = Path("data/chroma")
COLLECTION_NAME = "supportpulse_tickets"
BATCH_SIZE = 5000


def get_client() -> chromadb.PersistentClient:
    """Return a persistent ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_index(force_rebuild: bool = False) -> chromadb.Collection:
    """
    Build the ChromaDB vector index from pre-computed .npy embeddings.
    Loads all splits (train + val + test) — this is a knowledge base, not a training set.
    Skips rebuild if collection already exists unless force_rebuild=True.
    """
    client = get_client()

    if force_rebuild:
        try:
            client.delete_collection(COLLECTION_NAME)
            print("  [Index] Deleted existing collection for rebuild.")
        except Exception:
            pass

    try:
        col = client.get_collection(COLLECTION_NAME)
        count = col.count()
        if count > 0:
            print(f"  [Index] Collection exists with {count:,} vectors. Skipping rebuild.")
            print(f"  [Index] Pass force_rebuild=True to re-index.")
            return col
    except Exception:
        pass

    col = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}
    )

    total_inserted = 0
    start = time.time()

    for split in ["train", "val", "test"]:
        emb_path = GOLD_DIR / f"{split}_embeddings.npy"
        df_path = GOLD_DIR / f"{split}.parquet"

        if not emb_path.exists() or not df_path.exists():
            print(f"  [Index] WARNING: {split} files missing, skipping.")
            continue

        embeddings = np.load(emb_path)
        df = pd.read_parquet(df_path)

        n = len(embeddings)
        print(f"  [Index] {split}: {n:,} vectors @ {embeddings.shape[1]}-dim")

        for batch_start in range(0, n, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, n)
            batch_emb = embeddings[batch_start:batch_end]
            batch_df = df.iloc[batch_start:batch_end]

            ids = batch_df["ticket_id"].astype(str).tolist()
            vecs = batch_emb.tolist()
            metas = [
                {
                    "split": split,
                    "category": str(row.get("category", "")),
                    "priority": str(row.get("priority", "")),
                    "subject": str(row.get("subject", ""))[:200],
                }
                for _, row in batch_df.iterrows()
            ]

            col.upsert(ids=ids, embeddings=vecs, metadatas=metas)
            total_inserted += (batch_end - batch_start)

            elapsed = time.time() - start
            pct = (total_inserted / 68235) * 100
            rate = total_inserted / elapsed if elapsed > 0 else 1
            eta = (68235 - total_inserted) / rate
            print(
                f"  [Index] {pct:5.1f}% | {total_inserted:,}/68,235 vectors"
                f" | {rate:.0f} vec/s | ETA {eta:.0f}s",
                end="\r", flush=True
            )

    elapsed = time.time() - start
    final_count = col.count()
    print(f"\n  [Index] Done: {final_count:,} vectors indexed in {elapsed:.1f}s")
    return col


def load_index() -> chromadb.Collection:
    """Load existing ChromaDB collection (must have been built first)."""
    client = get_client()
    col = client.get_collection(COLLECTION_NAME)
    return col


if __name__ == "__main__":
    build_index()
