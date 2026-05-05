"""
Label Normaliser — src/data/label_normaliser.py
================================================
Maps raw, inconsistent GitHub/HF labels to our 10 canonical SupportPulse
categories using the lookup table in configs/label_mapping.json.

Why do we need this?
  - GitHub has 1000s of unique labels across repos: "crash", "defect",
    "wont-fix", "regression", "bug-report" — all meaning "bug".
  - Our ML model needs exactly 10 clean categories to learn from.
  - This module is the translation layer between noisy source data and
    our clean training targets.

The 10 canonical categories:
  bug, feature, security, billing, performance, docs,
  question, incident, sla_breach, ui
"""

import json
from pathlib import Path
from typing import List, Optional


def load_label_map(path: Optional[str] = None) -> dict:
    """
    Load the label-to-category mapping from configs/label_mapping.json.

    The JSON file contains a flat dict of raw_label → canonical_category,
    e.g.: {"crash": "bug", "enhancement": "feature", "sql-injection": "security"}

    Args:
        path: Optional override path to the label_mapping.json file.
              If None, resolves relative to the project root.

    Returns:
        A dict mapping lowercase raw labels to canonical category strings.
    """
    if path is None:
        # Resolve: from src/data/ go up two levels to project root, then configs/
        root = Path(__file__).resolve().parent.parent.parent
        path = root / "configs" / "label_mapping.json"

    with open(path, "r", encoding="utf-8") as f:
        raw_map = json.load(f)

    # Normalise all keys to lowercase for case-insensitive matching
    return {k.lower().strip(): v for k, v in raw_map.items()}


def normalise_labels(raw_labels: List[str], label_map: dict) -> str:
    """
    Map a list of raw labels from a ticket to a single canonical category.

    Strategy:
      - Iterate through each raw label (lowercased).
      - Return the first match found in label_map.
      - If no labels match, return "question" (safe default for unknown/ambiguous).

    Why "first match wins"?
      - GitHub issues often have multiple labels (e.g. ["bug", "good first issue"]).
      - The first label that maps to a real category is the most specific intent.
      - We trust the label ordering from the source repo.

    Args:
        raw_labels: List of raw label strings from the ticket source.
        label_map:  Dict loaded from load_label_map().

    Returns:
        A single canonical category string (one of the 10 valid categories).

    Example:
        >>> m = load_label_map()
        >>> normalise_labels(["bug", "regression"], m)
        'bug'
        >>> normalise_labels(["good first issue"], m)
        'question'
    """
    DEFAULT_CATEGORY = "question"

    if not raw_labels:
        return DEFAULT_CATEGORY

    for label in raw_labels:
        if not label:
            continue
        normalised = str(label).lower().strip()
        if normalised in label_map:
            return label_map[normalised]

    return DEFAULT_CATEGORY
