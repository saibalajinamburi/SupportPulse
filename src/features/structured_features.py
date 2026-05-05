"""
Structured Feature Engineering — src/features/structured_features.py
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import timezone


# Encodings for categorical fields that the LightGBM SLA model needs as numbers
TIER_ENCODING = {"free": 0, "pro": 1, "enterprise": 2}
SOURCE_ENCODING = {"github": 0, "hf_customer_support": 1, "synthetic": 2, "zendesk": 3}

_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```")


def build_structured_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all structured features from a Silver DataFrame.

    Args:
        df: Silver DataFrame with columns: body, subject, created_at,
            reopen_count, customer_tier, source, comments.

    Returns:
        A new DataFrame with only the feature columns (no text columns).
        This is the 'structured features' portion of the Gold layer.
    """
    print(f"  [Features] Computing structured features for {len(df):,} rows...")

    now = pd.Timestamp.now(tz="UTC")
    features = pd.DataFrame(index=df.index)

    body = df["body"].fillna("").astype(str)
    subject = df["subject"].fillna("").astype(str)
    full_text = subject + " " + body

    # ── Text statistics ────────────────────────────────────────────────────
    features["text_length"] = body.str.len()
    features["word_count"] = body.str.split().str.len().fillna(0).astype(int)
    features["subject_length"] = subject.str.len()

    # ── Code and technical signals ─────────────────────────────────────────
    features["code_block_count"] = body.apply(
        lambda t: len(_CODE_BLOCK_PATTERN.findall(t))
    )
    features["url_count"] = full_text.apply(
        lambda t: len(_URL_PATTERN.findall(t))
    )

    # ── Sentiment proxies ──────────────────────────────────────────────────
    features["question_mark_count"] = body.str.count(r"\?")
    features["exclamation_count"] = body.str.count(r"!")
    # Capitalised words often signal urgency ("URGENT", "CRITICAL", "DOWN")
    features["caps_word_count"] = body.apply(
        lambda t: sum(1 for w in t.split() if w.isupper() and len(w) > 2)
    )

    # ── Temporal features (critical for SLA prediction) ───────────────────
    created_at = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    created_at = created_at.fillna(pd.Timestamp("2020-01-01", tz="UTC"))

    features["hour_of_day"] = created_at.dt.hour       # 0–23
    features["day_of_week"] = created_at.dt.dayofweek  # 0=Mon, 6=Sun
    features["is_weekend"] = (created_at.dt.dayofweek >= 5).astype(int)
    features["is_after_hours"] = (
        (created_at.dt.hour < 9) | (created_at.dt.hour >= 18)
    ).astype(int)

    features["ticket_age_hours"] = (
        (now - created_at).dt.total_seconds() / 3600
    ).clip(lower=0).round(2)

    # ── Engagement features ────────────────────────────────────────────────
    features["reopen_count"] = df.get("reopen_count", pd.Series(0, index=df.index)).fillna(0).astype(int)
    features["comment_count"] = df.get("comments", pd.Series([[] for _ in range(len(df))], index=df.index)).apply(
        lambda c: len(c) if isinstance(c, list) else 0
    )

    # ── Categorical encodings (for LightGBM, which needs numbers) ─────────
    features["customer_tier_encoded"] = df.get(
        "customer_tier", pd.Series("free", index=df.index)
    ).map(TIER_ENCODING).fillna(0).astype(int)

    features["source_encoded"] = df["source"].map(SOURCE_ENCODING).fillna(0).astype(int)

    # ── Keep ticket_id for joining back to Silver ──────────────────────────
    features["ticket_id"] = df["ticket_id"].values

    print(f"  [Features] Structured features computed: {len(features.columns)} columns")
    return features
