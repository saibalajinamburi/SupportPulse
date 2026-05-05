"""Silver Pipeline."""

import json
import hashlib
import pandas as pd
from pathlib import Path
from typing import Optional
import sys
import os

# Add project root to path so sibling modules import correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.pii_masker import mask_pii
from src.data.label_normaliser import load_label_map, normalise_labels

# ── Routing rules: category → responsible team ──────────────────────────────
ROUTING_MAP = {
    "bug": "engineering",
    "performance": "engineering",
    "dependency": "engineering",
    "feature": "engineering",
    "ui": "engineering",
    "test": "engineering",
    "security": "security",
    "billing": "billing",
    "docs": "support",
    "question": "support",
    "incident": "infra",
    "sla_breach": "infra",
}

VALID_PRIORITIES = {"critical", "high", "medium", "low"}
DEFAULT_PRIORITY = "medium"


def _make_ticket_id(source: str, raw_id: str) -> str:
    """Create a deterministic ticket_id from source + original ID using SHA-1 prefix."""
    raw = f"{source}::{raw_id}"
    return hashlib.sha1(raw.encode()).hexdigest()[:16].upper()


def load_bronze(bronze_path: Path) -> pd.DataFrame:
    """Load the combined Bronze JSON file into a Pandas DataFrame."""
    print(f"  Loading Bronze: {bronze_path}")
    with open(bronze_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    print(f"  Loaded {len(df):,} Bronze rows")
    return df


def clean_to_silver(df: pd.DataFrame, label_map: Optional[dict] = None) -> pd.DataFrame:
    """Apply the full Bronze → Silver transformation pipeline."""
    if label_map is None:
        label_map = load_label_map()

    initial_count = len(df)
    print(f"\n  [Silver] Starting with {initial_count:,} rows")

    # ── Step A: Drop rows with null/empty body ─────────────────────────────
    df = df.dropna(subset=["body"])
    df = df[df["body"].astype(str).str.strip() != ""]
    dropped_null_body = initial_count - len(df)
    print(f"  [Silver] Dropped {dropped_null_body:,} rows with null/empty body")

    # ── Step B: Drop rows with body < 20 characters ────────────────────────
    df = df[df["body"].astype(str).str.len() >= 20]
    dropped_short = initial_count - dropped_null_body - len(df)
    print(f"  [Silver] Dropped {dropped_short:,} rows with body < 20 chars")

    # ── Step C & D: Apply PII masking to subject + body ────────────────────
    print("  [Silver] Masking PII in subject and body...")
    pii_count = 0

    def _apply_pii(row):
        nonlocal pii_count
        masked_body, flags_body = mask_pii(str(row.get("body", "")))
        masked_subj, flags_subj = mask_pii(str(row.get("subject", "")))
        all_flags = list(set(flags_body + flags_subj))
        if all_flags:
            pii_count += 1
        return pd.Series({
            "body": masked_body,
            "subject": masked_subj,
            "pii_flags": all_flags,
        })

    pii_result = df.apply(_apply_pii, axis=1)
    df["body"] = pii_result["body"]
    df["subject"] = pii_result["subject"]
    df["pii_flags"] = pii_result["pii_flags"]
    print(f"  [Silver] PII detected and masked in {pii_count:,} tickets")

    # ── Step E: Normalise labels to canonical category ─────────────────────
    print("  [Silver] Normalising labels...")
    df["category"] = df["labels_raw"].apply(
        lambda labels: normalise_labels(labels if isinstance(labels, list) else [], label_map)
    )

    # ── Step F: Parse created_at to datetime ──────────────────────────────
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    # For tickets without a date (HF datasets), assign epoch start as placeholder
    df["created_at"] = df["created_at"].fillna(pd.Timestamp("2020-01-01", tz="UTC"))

    # ── Step G: Assign default priority ───────────────────────────────────
    if "priority" not in df.columns:
        df["priority"] = DEFAULT_PRIORITY
    else:
        df["priority"] = df["priority"].apply(
            lambda p: p if isinstance(p, str) and p.lower() in VALID_PRIORITIES else DEFAULT_PRIORITY
        )

    # ── Step H: Assign routing_team based on category ─────────────────────
    df["routing_team"] = df["category"].map(ROUTING_MAP).fillna("support")

    # ── Step I: Ensure ticket_id exists and is unique ─────────────────────
    if "ticket_id" not in df.columns:
        df["ticket_id"] = df.apply(
            lambda r: _make_ticket_id(str(r.get("source", "unknown")), str(r.name)), axis=1
        )
    else:
        # Fill any null ticket_ids
        mask_null = df["ticket_id"].isna() | (df["ticket_id"].astype(str).str.strip() == "")
        df.loc[mask_null, "ticket_id"] = df[mask_null].apply(
            lambda r: _make_ticket_id(str(r.get("source", "unknown")), str(r.name)), axis=1
        )

    # ── Step J: Deduplicate by (subject + body) ───────────────────────────
    before_dedup = len(df)
    df["_dedup_key"] = df["subject"].astype(str) + "|||" + df["body"].astype(str)
    df = df.drop_duplicates(subset=["_dedup_key"])
    df = df.drop(columns=["_dedup_key"])
    dupes_dropped = before_dedup - len(df)
    print(f"  [Silver] Removed {dupes_dropped:,} duplicate tickets")

    # ── Step K: Fill required columns with defaults ────────────────────────
    if "comments" not in df.columns:
        df["comments"] = [[] for _ in range(len(df))]
    if "reopen_count" not in df.columns:
        df["reopen_count"] = 0
    if "customer_tier" not in df.columns:
        df["customer_tier"] = "free"

    # ── Ensure pii_flags is always a string (Parquet-safe) ─────────────────
    df["pii_flags"] = df["pii_flags"].apply(
        lambda x: ",".join(x) if isinstance(x, list) else ""
    )

    # ── Final Silver schema (select and order columns) ─────────────────────
    silver_cols = [
        "ticket_id", "source", "created_at", "subject", "body",
        "category", "priority", "routing_team",
        "labels_raw", "pii_flags", "reopen_count", "customer_tier",
    ]
    # Add any columns that exist but aren't in our list (keep all data)
    extra_cols = [c for c in df.columns if c not in silver_cols]
    final_cols = silver_cols + extra_cols
    final_cols = [c for c in final_cols if c in df.columns]
    df = df[final_cols]

    print(f"\n  [Silver] Final row count: {len(df):,}")
    print(f"  [Silver] Total dropped: {initial_count - len(df):,} rows")
    return df


def write_silver(df: pd.DataFrame, silver_dir: Path = Path("data/silver")) -> Path:
    """Write the Silver DataFrame to Parquet."""
    silver_dir.mkdir(parents=True, exist_ok=True)

    # Write combined file
    combined_path = silver_dir / "all_silver.parquet"
    df.to_parquet(combined_path, index=False, compression="snappy")
    size_mb = combined_path.stat().st_size / (1024 * 1024)
    print(f"\n  [Silver Writer] Written: {combined_path} ({size_mb:.1f} MB, {len(df):,} rows)")

    # Write per-source partitions
    for source in df["source"].unique():
        partition = df[df["source"] == source]
        partition_path = silver_dir / f"{source}_tickets.parquet"
        partition.to_parquet(partition_path, index=False, compression="snappy")
        print(f"  [Silver Writer] Partition: {partition_path} ({len(partition):,} rows)")

    return combined_path


if __name__ == "__main__":
    bronze_path = Path("data/bronze/all_bronze_combined.json")
    label_map = load_label_map()

    raw_df = load_bronze(bronze_path)
    silver_df = clean_to_silver(raw_df, label_map)
    write_silver(silver_df)

    print("\nSilver Pipeline COMPLETE.")
