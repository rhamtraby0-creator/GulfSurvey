"""
Database module for Bidboland Persian Gulf Gas Refining Survey System
Uses SQLite for local/Termux deployment.
"""

import os
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "survey.db"

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                last_password_change TEXT,
                failed_attempts INTEGER DEFAULT 0,
                lock_until TEXT,
                session_token TEXT,
                session_expires TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT UNIQUE NOT NULL,
                q1 INTEGER NOT NULL CHECK (q1 BETWEEN 1 AND 4),
                q2 INTEGER NOT NULL CHECK (q2 BETWEEN 1 AND 4),
                q3 INTEGER NOT NULL CHECK (q3 BETWEEN 1 AND 4),
                q4 INTEGER NOT NULL CHECK (q4 BETWEEN 1 AND 4),
                q5 INTEGER NOT NULL CHECK (q5 BETWEEN 1 AND 4),
                q6 INTEGER NOT NULL CHECK (q6 BETWEEN 1 AND 4),
                q7 INTEGER NOT NULL CHECK (q7 BETWEEN 1 AND 4),
                q8 INTEGER NOT NULL CHECK (q8 BETWEEN 1 AND 4),
                q9 INTEGER NOT NULL CHECK (q9 BETWEEN 1 AND 4),
                q10 INTEGER NOT NULL CHECK (q10 BETWEEN 1 AND 4),
                q11 INTEGER NOT NULL CHECK (q11 BETWEEN 1 AND 4),
                feedback TEXT,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'registered' CHECK (status IN ('registered', 'pending', 'error')),
                average_score REAL GENERATED ALWAYS AS (
                    (q1 + q2 + q3 + q4 + q5 + q6 + q7 + q8 + q9 + q10 + q11) / 11.0
                ) STORED
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_created ON responses(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_responses_participant ON responses(participant_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                size_bytes INTEGER,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'success'
            )
        """)
    return True

def get_next_participant_id(conn):
    row = conn.execute("SELECT MAX(CAST(participant_id AS INTEGER)) as max_id FROM responses").fetchone()
    next_id = 1 if row["max_id"] is None else row["max_id"] + 1
    return f"{next_id:06d}"

def log_event(event_type: str, message: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO system_logs (event_type, message, created_at) VALUES (?, ?, ?)",
            (event_type, message, datetime.now(timezone.utc).isoformat())
        )

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
