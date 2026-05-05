"""Time-Based Train/Val/Test Splitter."""

import pandas as pd
from pathlib import Path
from typing import Tuple


def time_based_split(
    df: pd.DataFrame,
    date_col: str = "created_at",
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split a DataFrame chronologically into train, val, and test sets."""
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
    """Save the three split DataFrames to Parquet files in the Gold directory."""
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
