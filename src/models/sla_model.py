"""LightGBM SLA Breach Model — inference."""

import joblib
import numpy as np
import pandas as pd
from pathlib import Path

FEATURE_COLS = [
    "text_length", "word_count", "subject_length",
    "code_block_count", "url_count", "question_mark_count",
    "exclamation_count", "caps_word_count",
    "hour_of_day", "day_of_week", "is_weekend", "is_after_hours",
    "ticket_age_hours", "reopen_count", "comment_count",
    "customer_tier_encoded", "source_encoded"
]

MODEL_PATH = Path("models/sla_model.joblib")
_model = None


def _load_model():
    """Lazy-load the trained model once."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"SLA model not found at {MODEL_PATH}. Run train_sla.py first."
            )
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_sla_risk(features: dict) -> dict:
    """Predict SLA breach risk for a single ticket given its structured features."""
    model = _load_model()
    row = {col: features.get(col, 0) for col in FEATURE_COLS}
    df = pd.DataFrame([row])
    prob = model.predict_proba(df)[0][1]
    breach_flag = bool(prob >= 0.5)
    return {
        "sla_risk_score": round(float(prob), 4),
        "breach_flag": breach_flag,
        "risk_level": "critical" if prob >= 0.8 else "high" if prob >= 0.6 else "medium" if prob >= 0.4 else "low"
    }


def predict_batch(feature_rows: list[dict]) -> list[dict]:
    """Predict SLA breach risk for a batch of feature dicts."""
    model = _load_model()
    df = pd.DataFrame([
        {col: row.get(col, 0) for col in FEATURE_COLS}
        for row in feature_rows
    ])
    probas = model.predict_proba(df)[:, 1]
    return [
        {
            "sla_risk_score": round(float(p), 4),
            "breach_flag": bool(p >= 0.5),
            "risk_level": "critical" if p >= 0.8 else "high" if p >= 0.6 else "medium" if p >= 0.4 else "low"
        }
        for p in probas
    ]
