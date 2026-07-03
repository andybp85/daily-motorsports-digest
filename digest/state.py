import sqlite3
from datetime import UTC, datetime, timedelta


class StateStore:
    """SQLite record of sent stories, for the cross-day suppress window."""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_stories (
                story_key TEXT NOT NULL,
                buzz_score REAL NOT NULL,
                sent_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def last_sent(self, key: str, within_days: int) -> float | None:
        cutoff = (datetime.now(UTC) - timedelta(days=within_days)).isoformat()
        row = self.conn.execute(
            "SELECT buzz_score FROM sent_stories "
            "WHERE story_key = ? AND sent_at >= ? "
            "ORDER BY sent_at DESC LIMIT 1",
            (key, cutoff),
        ).fetchone()
        return row[0] if row else None

    def record_sent(self, key: str, buzz: float, sent_at: datetime) -> None:
        self.conn.execute(
            "INSERT INTO sent_stories (story_key, buzz_score, sent_at) VALUES (?, ?, ?)",
            (key, buzz, sent_at.isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
