"""Label Normaliser."""

import json
from pathlib import Path
from typing import List, Optional


def load_label_map(path: Optional[str] = None) -> dict:
    """Load the label-to-category mapping from configs/label_mapping.json."""
    if path is None:
        # Resolve: from src/data/ go up two levels to project root, then configs/
        root = Path(__file__).resolve().parent.parent.parent
        path = root / "configs" / "label_mapping.json"

    with open(path, "r", encoding="utf-8") as f:
        raw_map = json.load(f)

    # Normalise all keys to lowercase for case-insensitive matching
    return {k.lower().strip(): v for k, v in raw_map.items()}


def normalise_labels(raw_labels: List[str], label_map: dict) -> str:
    """Map a list of raw labels from a ticket to a single canonical category."""
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
