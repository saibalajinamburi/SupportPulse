"""
Unit tests for the SQLite request logger (Phase 8 observability).
All tests use a temp DB — no prod data touched.
"""
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Redirect DB_PATH to a temp file for every test."""
    db = tmp_path / "test_requests.db"
    import src.monitoring.request_logger as rl
    monkeypatch.setattr(rl, "DB_PATH", db)
    return db


def _sample_log(temp_db):
    from src.monitoring.request_logger import log_triage
    log_triage(
        ticket_id="T-001",
        subject="Server is down",
        category="incident",
        priority="critical",
        routing_team="engineering",
        auto_escalate=True,
        sla_risk=0.82,
        confidence=0.95,
        timings={"classify_ms": 1000, "retrieve_ms": 4000, "total_ms": 5000},
        run_rag=False,
    )


def test_log_creates_db_file(temp_db):
    _sample_log(temp_db)
    assert temp_db.exists()


def test_log_and_retrieve(temp_db):
    from src.monitoring.request_logger import log_triage, get_recent
    _sample_log(temp_db)
    rows = get_recent(10)
    assert len(rows) == 1
    assert rows[0]["ticket_id"] == "T-001"
    assert rows[0]["category"] == "incident"
    assert rows[0]["auto_escalate"] == 1


def test_stats_correct(temp_db):
    from src.monitoring.request_logger import log_triage, get_stats
    # Log 2 tickets, 1 escalated
    log_triage("T-001", "s1", "incident", "critical", "engineering",
               True, 0.8, 0.9, {"total_ms": 5000}, False)
    log_triage("T-002", "s2", "billing", "medium", "billing",
               False, 0.2, 0.95, {"total_ms": 3000}, False)

    stats = get_stats()
    assert stats["total"] == 2
    assert stats["escalated"] == 1
    assert abs(stats["escalation_rate"] - 0.5) < 0.01
    assert abs(stats["avg_latency_ms"] - 4000) < 1
    assert "incident" in stats["category_counts"]
    assert "billing" in stats["category_counts"]


def test_empty_db_stats(temp_db):
    from src.monitoring.request_logger import get_stats
    stats = get_stats()
    assert stats["total"] == 0
    assert stats["escalated"] == 0
    assert stats["escalation_rate"] == 0
    assert stats["category_counts"] == {}


def test_get_recent_limit(temp_db):
    from src.monitoring.request_logger import log_triage, get_recent
    for i in range(10):
        log_triage(f"T-{i:03d}", "subj", "question", "low", "support",
                   False, 0.1, 0.9, {"total_ms": 1000}, False)
    rows = get_recent(5)
    assert len(rows) == 5
