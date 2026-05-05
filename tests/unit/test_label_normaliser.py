"""Unit Tests — Label Normaliser"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.data.label_normaliser import load_label_map, normalise_labels


def test_bug_maps_correctly():
    m = load_label_map()
    assert normalise_labels(["bug"], m) == "bug"


def test_feature_maps_correctly():
    m = load_label_map()
    result = normalise_labels(["enhancement"], m)
    assert result == "feature"


def test_unknown_label_returns_question():
    m = load_label_map()
    assert normalise_labels(["wontfix"], m) == "question"


def test_empty_labels_returns_question():
    m = load_label_map()
    assert normalise_labels([], m) == "question"


def test_first_match_wins():
    m = load_label_map()
    # "bug" is in map, "good first issue" may not be
    result = normalise_labels(["bug", "good first issue"], m)
    assert result == "bug"


def test_security_maps_correctly():
    m = load_label_map()
    result = normalise_labels(["security"], m)
    assert result == "security"


def test_case_insensitive():
    m = load_label_map()
    result = normalise_labels(["BUG"], m)
    assert result == "bug"
