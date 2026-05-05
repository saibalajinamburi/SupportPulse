"""Feast Feature Definitions — feature_store/ticket_features.py"""

from datetime import timedelta
from pathlib import Path

from feast import Entity, Feature, FeatureView, FileSource, Field
from feast.types import Float32, Int64, String


# ── Absolute path to Gold features parquet ────────────────────────────────
# Feast needs an absolute path (or relative from feast apply invocation dir).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TRAIN_FEATURES_PATH = str(_PROJECT_ROOT / "data" / "gold" / "train_features.parquet")


# ── Entity: the thing we look features up BY ──────────────────────────────
# An Entity is the primary key. In our case, every feature lookup is
# "give me the features for ticket_id = XYZ".
ticket = Entity(
    name="ticket",
    join_keys=["ticket_id"],
    description="A support ticket identified by its unique ticket_id.",
)


# ── Data Source: where Feast reads features FROM (offline) ─────────────────
ticket_features_source = FileSource(
    name="ticket_structured_features_source",
    path=_TRAIN_FEATURES_PATH,
    timestamp_field="event_timestamp",
)


# ── Feature View: the schema of features we want to serve ─────────────────
ticket_structured_fv = FeatureView(
    name="ticket_structured_features",
    entities=[ticket],
    ttl=timedelta(days=90),  # Features expire after 90 days (rerun materialise)
    schema=[
        Field(name="text_length",            dtype=Int64),
        Field(name="word_count",             dtype=Int64),
        Field(name="subject_length",         dtype=Int64),
        Field(name="code_block_count",       dtype=Int64),
        Field(name="url_count",              dtype=Int64),
        Field(name="question_mark_count",    dtype=Int64),
        Field(name="exclamation_count",      dtype=Int64),
        Field(name="caps_word_count",        dtype=Int64),
        Field(name="hour_of_day",            dtype=Int64),
        Field(name="day_of_week",            dtype=Int64),
        Field(name="is_weekend",             dtype=Int64),
        Field(name="is_after_hours",         dtype=Int64),
        Field(name="ticket_age_hours",       dtype=Float32),
        Field(name="reopen_count",           dtype=Int64),
        Field(name="comment_count",          dtype=Int64),
        Field(name="customer_tier_encoded",  dtype=Int64),
        Field(name="source_encoded",         dtype=Int64),
    ],
    source=ticket_features_source,
    description="Structured numerical features for SLA risk prediction and routing.",
)
