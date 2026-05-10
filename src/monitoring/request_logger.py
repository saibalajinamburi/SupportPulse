"""
Request logger — persists every API triage call to a local SQLite DB.
Used by the dashboard to show recent activity, latency trends, and category distribution.
No external dependencies — uses Python's built-in sqlite3.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/requests.db")


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the requests table if it doesn't exist."""
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS triage_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                ticket_id   TEXT,
                subject     TEXT,
                category    TEXT,
                priority    TEXT,
                routing_team TEXT,
                auto_escalate INTEGER,
                sla_risk    REAL,
                confidence  REAL,
                total_ms    REAL,
                classify_ms REAL,
                retrieve_ms REAL,
                rag_ms      REAL,
                run_rag     INTEGER
            )
        """)
        conn.commit()


def log_triage(
    ticket_id: str,
    subject: str,
    category: str,
    priority: str,
    routing_team: str,
    auto_escalate: bool,
    sla_risk: float,
    confidence: float,
    timings: dict,
    run_rag: bool,
):
    """Insert one triage result into the log table."""
    init_db()
    with _get_conn() as conn:
        conn.execute("""
            INSERT INTO triage_log
              (ts, ticket_id, subject, category, priority, routing_team,
               auto_escalate, sla_risk, confidence,
               total_ms, classify_ms, retrieve_ms, rag_ms, run_rag)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            datetime.utcnow().isoformat(),
            ticket_id, subject[:200], category, priority, routing_team,
            int(auto_escalate), round(sla_risk, 4), round(confidence, 4),
            timings.get("total_ms", 0),
            timings.get("classify_ms", 0),
            timings.get("retrieve_ms", 0),
            timings.get("rag_ms", 0),
            int(run_rag),
        ))
        conn.commit()


def get_recent(limit: int = 50) -> list[dict]:
    """Fetch the most recent triage log entries."""
    init_db()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM triage_log ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Aggregate stats for the dashboard summary panel."""
    init_db()
    with _get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM triage_log").fetchone()[0]
        escalated = conn.execute(
            "SELECT COUNT(*) FROM triage_log WHERE auto_escalate=1"
        ).fetchone()[0]
        avg_ms = conn.execute(
            "SELECT AVG(total_ms) FROM triage_log"
        ).fetchone()[0] or 0
        cat_rows = conn.execute(
            "SELECT category, COUNT(*) as n FROM triage_log GROUP BY category ORDER BY n DESC"
        ).fetchall()

    return {
        "total": total,
        "escalated": escalated,
        "escalation_rate": round(escalated / total, 3) if total else 0,
        "avg_latency_ms": round(avg_ms, 0),
        "category_counts": {r["category"]: r["n"] for r in cat_rows},
    }
