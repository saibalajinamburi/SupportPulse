"""
Time-Based Train/Val/Test Splitter — src/data/splitter.py
==========================================================
Splits the Silver dataset into training, validation, and test sets
using a chronological (time-based) split instead of random sampling.

Why time-based split instead of random split?
  - Support tickets have temporal patterns: new bug categories emerge,
    language trends shift, product features change over time.
  - With a RANDOM split, your test set contains tickets from the same
    time period as training. The model "sees the future" during training.
  - With a TIME-BASED split:
      * Train = oldest 70% of data (model learns from history)
      * Val   = next 15% (tune hyperparameters on near-future)
      * Test  = newest 15% (evaluate on true unseen future)
  - This is how Netflix, Google, and Uber evaluate recommendation/ranking
    models — never shuffle time-series data randomly.

Split ratio: 70 / 15 / 15
"""

import pandas as pd
from pathlib import Path
from typing import Tuple


def time_based_split(
    df: pd.DataFrame,
    date_col: str = "created_at",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split a DataFrame chronologically into train, val, and test sets.

    Args:
        df:          The Silver DataFrame (must have a datetime column).
        date_col:    Name of the datetime column to sort by.
        train_ratio: Fraction of data for training (default 0.70).
        val_ratio:   Fraction for validation (default 0.15). Test gets remainder.

    Returns:
        A tuple of (train_df, val_df, test_df).
    """
    # Sort by date ascending (oldest first)
    df_sorted = df.sort_values(date_col, ascending=True).reset_index(drop=True)

    n = len(df_sorted)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))

    train_df = df_sorted.iloc[:train_end].copy()
    val_df = df_sorted.iloc[train_end:val_end].copy()
    test_df = df_sorted.iloc[val_end:].copy()

    print(f"\n  [Splitter] Total rows: {n:,}")
    print(f"  [Splitter] Train: {len(train_df):,} rows  "
          f"({train_df[date_col].min().date()} → {train_df[date_col].max().date()})")
    print(f"  [Splitter] Val:   {len(val_df):,} rows  "
          f"({val_df[date_col].min().date()} → {val_df[date_col].max().date()})")
    print(f"  [Splitter] Test:  {len(test_df):,} rows  "
          f"({test_df[date_col].min().date()} → {test_df[date_col].max().date()})")

    return train_df, val_df, test_df


def save_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    gold_dir: Path = Path("data/gold"),
) -> None:
    """
    Save the three split DataFrames to Parquet files in the Gold directory.

    Args:
        train_df:  Training set DataFrame.
        val_df:    Validation set DataFrame.
        test_df:   Test set DataFrame.
        gold_dir:  Output directory (created if not exists).
    """
    gold_dir.mkdir(parents=True, exist_ok=True)

    for name, split_df in [("train", train_df), ("val", val_df), ("test", test_df)]:
        path = gold_dir / f"{name}.parquet"
        split_df.to_parquet(path, index=False, compression="snappy")
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"  [Splitter] Saved: {path} ({size_mb:.1f} MB, {len(split_df):,} rows)")


if __name__ == "__main__":
    silver_path = Path("data/silver/all_silver.parquet")
    print(f"Loading {silver_path}...")
    df = pd.read_parquet(silver_path)
    train, val, test = time_based_split(df)
    save_splits(train, val, test)
    print("\nSplit COMPLETE.")
