"""Gold Feature Pipeline — src/features/gold_pipeline.py"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.splitter import time_based_split, save_splits
from src.features.structured_features import build_structured_features
from src.features.embedding import embed_texts, check_ollama_running


GOLD_DIR = Path("data/gold")
SILVER_PATH = Path("data/silver/all_silver.parquet")


def build_gold(silver_path: Path = SILVER_PATH, gold_dir: Path = GOLD_DIR) -> None:
    """Full Silver → Gold transformation pipeline."""
    gold_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()

    # ── Step 1: Load Silver ────────────────────────────────────────────────
    print(f"\n{'='*55}")
    print("GOLD PIPELINE: Starting Silver -> Gold transformation")
    print(f"{'='*55}")
    print(f"\n[Gold] Loading Silver data from {silver_path}...")
    df = pd.read_parquet(silver_path)
    print(f"[Gold] Loaded {len(df):,} Silver rows")

    # ── Step 2: Time-based split ──────────────────────────────────────────
    print("\n[Gold] Performing time-based train/val/test split...")
    train_df, val_df, test_df = time_based_split(df)
    save_splits(train_df, val_df, test_df, gold_dir)

    # ── Step 3: Structured features ───────────────────────────────────────
    print("\n[Gold] Computing structured features...")
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        feats = build_structured_features(split_df)
        feat_path = gold_dir / f"{split_name}_features.parquet"
        feats.to_parquet(feat_path, index=False, compression="snappy")
        size_mb = feat_path.stat().st_size / (1024 * 1024)
        print(f"  [Gold] Saved {feat_path} ({size_mb:.1f} MB, {len(feats):,} rows, {len(feats.columns)} cols)")

    # ── Step 4: BGE-M3 Embeddings ─────────────────────────────────────────
    print("\n[Gold] Checking Ollama / BGE-M3 availability...")
    if not check_ollama_running():
        print("\n[Gold] SKIPPING embeddings — Ollama not running.")
        print("[Gold] To generate embeddings later, run:")
        print("       python -m src.features.gold_pipeline --embeddings-only")
        _save_summary(gold_dir, train_df, val_df, test_df, embeddings_skipped=True)
        return

    print("\n[Gold] Computing BGE-M3 embeddings for all splits...")
    for split_name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        # Concatenate subject + body for richer embedding context
        texts = (
            split_df["subject"].fillna("").astype(str)
            + " [SEP] "
            + split_df["body"].fillna("").astype(str)
        ).tolist()

        emb_start = time.time()
        embeddings = embed_texts(texts)
        emb_secs = time.time() - emb_start

        emb_path = gold_dir / f"{split_name}_embeddings.npy"
        np.save(emb_path, embeddings)
        size_mb = emb_path.stat().st_size / (1024 * 1024)
        print(f"  [Gold] Saved {emb_path} shape={embeddings.shape} "
              f"({size_mb:.1f} MB, took {emb_secs:.0f}s)")

    total_secs = time.time() - start
    print(f"\n[Gold] Pipeline COMPLETE in {total_secs/60:.1f} minutes")
    _save_summary(gold_dir, train_df, val_df, test_df, embeddings_skipped=False)


def _save_summary(gold_dir, train_df, val_df, test_df, embeddings_skipped):
    """Write a human-readable summary of what was created."""
    summary_path = gold_dir / "gold_summary.txt"
    with open(summary_path, "w") as f:
        f.write("Gold Layer Summary\n")
        f.write("=" * 40 + "\n")
        f.write(f"Train rows:  {len(train_df):,}\n")
        f.write(f"Val rows:    {len(val_df):,}\n")
        f.write(f"Test rows:   {len(test_df):,}\n")
        f.write(f"Total:       {len(train_df)+len(val_df)+len(test_df):,}\n")
        f.write(f"Embeddings:  {'SKIPPED (run with Ollama)' if embeddings_skipped else 'Generated'}\n")
    print(f"\n[Gold] Summary saved to {summary_path}")


if __name__ == "__main__":
    build_gold()
