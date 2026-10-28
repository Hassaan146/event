import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DATABASE_PATH


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def initialize_database() -> None:
    with connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                event_date TEXT,
                end_date TEXT,
                category TEXT,
                venue TEXT,
                format TEXT,
                eligibility TEXT,
                team_size TEXT,
                level TEXT,
                registration_status TEXT NOT NULL DEFAULT 'unknown',
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_text TEXT NOT NULL,
                last_checked TEXT NOT NULL,
                first_seen TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                publisher TEXT NOT NULL,
                enabled INTEGER NOT NULL,
                last_checked TEXT,
                last_error TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date)")
