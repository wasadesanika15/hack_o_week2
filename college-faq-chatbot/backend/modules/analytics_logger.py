"""
Analytics logger for the College FAQ Chatbot (Task 10).

Dual-sink logging: every interaction is written to both:
  1. ``logs/interactions.csv``  — human-readable, easy to process with pandas
  2. ``logs/interactions.db``   — SQLite database for structured queries

Schema:
  id | timestamp | session_id | query | intent | score | answer | fallback_triggered
"""

from __future__ import annotations

import csv
import os
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────
_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_CSV_PATH = _LOG_DIR / "interactions.csv"
_DB_PATH = _LOG_DIR / "interactions.db"

# Concurrency guard for file writes
_lock = threading.Lock()

# Fallback threshold — interactions with score below this are flagged
FALLBACK_THRESHOLD = 0.35

# CSV columns (order matters)
_CSV_COLUMNS = [
    "id",
    "timestamp",
    "session_id",
    "query",
    "intent",
    "score",
    "answer",
    "fallback_triggered",
]


# ──────────────────────────────────────────────────────────────────────
# SQLite setup
# ──────────────────────────────────────────────────────────────────────
def _ensure_db() -> sqlite3.Connection:
    """Return a SQLite connection, creating the table if it doesn't exist."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id              TEXT    PRIMARY KEY,
            timestamp       TEXT    NOT NULL,
            session_id      TEXT    NOT NULL,
            query           TEXT    NOT NULL,
            intent          TEXT    NOT NULL,
            score           REAL    NOT NULL,
            answer          TEXT    NOT NULL,
            fallback_triggered INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    return conn


# Module-level DB connection (lazy)
_db_conn: Optional[sqlite3.Connection] = None


def _get_db() -> sqlite3.Connection:
    global _db_conn
    if _db_conn is None:
        _db_conn = _ensure_db()
    return _db_conn


# ──────────────────────────────────────────────────────────────────────
# CSV setup
# ──────────────────────────────────────────────────────────────────────
def _ensure_csv() -> None:
    """Create the CSV file with a header row if it does not exist."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not _CSV_PATH.is_file():
        with _CSV_PATH.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(_CSV_COLUMNS)


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────
def log_interaction(
    query: str,
    intent: str,
    score: float,
    answer: str,
    session_id: str,
) -> dict:
    """
    Log a single chatbot interaction to CSV and SQLite.

    Parameters
    ----------
    query : str
        The user's raw question.
    intent : str
        Detected intent label.
    score : float
        TF-IDF cosine-similarity confidence score.
    answer : str
        The bot's answer text.
    session_id : str
        Unique session identifier.

    Returns
    -------
    dict
        The logged row as a dictionary (useful for chaining / testing).
    """
    row_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat()
    fallback_triggered = score < FALLBACK_THRESHOLD

    row = {
        "id": row_id,
        "timestamp": ts,
        "session_id": session_id,
        "query": query,
        "intent": intent,
        "score": round(score, 4),
        "answer": answer,
        "fallback_triggered": fallback_triggered,
    }

    with _lock:
        _write_csv(row)
        _write_db(row)

    return row


def _write_csv(row: dict) -> None:
    """Append one row to the CSV log."""
    _ensure_csv()
    with _CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([row[c] for c in _CSV_COLUMNS])


def _write_db(row: dict) -> None:
    """Insert one row into the SQLite database."""
    conn = _get_db()
    conn.execute(
        """
        INSERT INTO interactions (id, timestamp, session_id, query, intent, score, answer, fallback_triggered)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            row["id"],
            row["timestamp"],
            row["session_id"],
            row["query"],
            row["intent"],
            row["score"],
            row["answer"],
            int(row["fallback_triggered"]),
        ),
    )
    conn.commit()


# ──────────────────────────────────────────────────────────────────────
# Query helpers (useful for analysis.ipynb or testing)
# ──────────────────────────────────────────────────────────────────────
def get_all_interactions() -> list[dict]:
    """Return every logged interaction as a list of dicts."""
    conn = _get_db()
    cursor = conn.execute("SELECT * FROM interactions ORDER BY timestamp DESC")
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_fallback_rate() -> float:
    """Return the percentage of interactions that triggered a fallback (0.0 – 1.0)."""
    conn = _get_db()
    total = conn.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    if total == 0:
        return 0.0
    fallbacks = conn.execute(
        "SELECT COUNT(*) FROM interactions WHERE fallback_triggered = 1"
    ).fetchone()[0]
    return fallbacks / total


# ──────────────────────────────────────────────────────────────────────
# Stand-alone demo
# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Log a few sample interactions
    samples = [
        ("What are the college timings?", "timings", 0.87, "College opens at 8 AM.", "demo-001"),
        ("Tell me about fees", "fees", 0.72, "Tuition fee is ₹50,000/semester.", "demo-001"),
        ("xyzzy gibberish", "general", 0.08, "I'm not sure what you mean.", "demo-002"),
        ("Hostel allotment?", "hostel", 0.45, "Hostel allotment starts July 1.", "demo-002"),
        ("Placement stats?", "placement", 0.25, "Fallback triggered.", "demo-003"),
    ]
    for q, i, s, a, sid in samples:
        result = log_interaction(q, i, s, a, sid)
        print(f"  Logged: {result['id'][:8]}… | {q[:30]} | fallback={result['fallback_triggered']}")

    print(f"\nFallback rate: {get_fallback_rate():.1%}")
    print(f"CSV: {_CSV_PATH}")
    print(f"DB:  {_DB_PATH}")
