"""SQLite-backed rate limiter fallback for environments without Redis.

This class exposes async methods compatible with `RedisRateLimiter` so it can be
used in the same middleware or in the Flask decorator (via asyncio.run).

It stores per-window counters and a blocked_until timestamp in a local SQLite
database. Use an in-memory DB for tests or specify a path for persistence.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from typing import Optional, Tuple
from pathlib import Path


class SQLiteRateLimiter:
    def __init__(self, db_path: Optional[str] = None, window_seconds: int = 60, max_requests: int = 5):
        self.window = int(window_seconds)
        self.max_requests = int(max_requests)
        self.db_path = db_path or ":memory:"
        # If using in-memory DB, keep a single shared connection so tables persist
        self._shared_conn = None
        if self.db_path == ":memory":
            self.db_path = ":memory:"
        if self.db_path == ":memory:":
            self._shared_conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
            self._shared_conn.row_factory = sqlite3.Row
        # initialize DB synchronously
        self._init_db()

    def _conn(self):
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path, timeout=5, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                api_key TEXT NOT NULL,
                window_start INTEGER NOT NULL,
                count INTEGER NOT NULL,
                blocked_until INTEGER DEFAULT 0,
                PRIMARY KEY (api_key, window_start)
            )
            """
        )
        conn.commit()
        # Close only if not using shared in-memory connection
        if self._shared_conn is None:
            conn.close()

    def _window_start(self, now: Optional[float] = None) -> int:
        if now is None:
            now = time.time()
        return int(now // self.window) * self.window

    async def increment_and_check(self, api_key: str) -> Tuple[bool, int, Optional[int]]:
        """Async-compatible wrapper that runs DB ops in a thread.

        Returns same shape as RedisRateLimiter.increment_and_check
        """
        return await asyncio.to_thread(self._increment_and_check_sync, api_key)

    def _increment_and_check_sync(self, api_key: str) -> Tuple[bool, int, Optional[int]]:
        now = int(time.time())
        window_start = self._window_start(now)
        conn = self._conn()
        cur = conn.cursor()

        # Check if there is a blocked_until entry in any previous window
        cur.execute("SELECT blocked_until FROM api_usage WHERE api_key = ? ORDER BY window_start DESC LIMIT 1", (api_key,))
        row = cur.fetchone()
        if row and row["blocked_until"] and int(row["blocked_until"]) > now:
            retry_after = int(row["blocked_until"]) - now
            if self._shared_conn is None:
                conn.close()
            return False, 0, retry_after

        # Get current counter
        cur.execute("SELECT count FROM api_usage WHERE api_key = ? AND window_start = ?", (api_key, window_start))
        row = cur.fetchone()
        if row:
            cur_count = int(row["count"])
            cur_count += 1
            cur.execute("UPDATE api_usage SET count = ? WHERE api_key = ? AND window_start = ?", (cur_count, api_key, window_start))
        else:
            cur_count = 1
            cur.execute("INSERT INTO api_usage (api_key, window_start, count, blocked_until) VALUES (?, ?, ?, 0)", (api_key, window_start, cur_count))

        conn.commit()

        remaining = max(0, self.max_requests - cur_count)
        if cur_count > self.max_requests:
            blocked_ts = now + self.window
            # Set blocked_until on current row
            cur.execute("UPDATE api_usage SET blocked_until = ? WHERE api_key = ? AND window_start = ?", (blocked_ts, api_key, window_start))
            conn.commit()
            if self._shared_conn is None:
                conn.close()
            return False, 0, self.window

        if self._shared_conn is None:
            conn.close()
        return True, remaining, None

    async def is_blocked(self, api_key: str) -> Optional[int]:
        return await asyncio.to_thread(self._is_blocked_sync, api_key)

    def _is_blocked_sync(self, api_key: str) -> Optional[int]:
        now = int(time.time())
        conn = self._conn()
        cur = conn.cursor()
        cur.execute("SELECT blocked_until FROM api_usage WHERE api_key = ? ORDER BY window_start DESC LIMIT 1", (api_key,))
        row = cur.fetchone()
        if self._shared_conn is None:
            conn.close()
        if not row:
            return None
        try:
            blocked_ts = int(row["blocked_until"])
        except Exception:
            return None
        if blocked_ts > now:
            return blocked_ts - now
        return None


__all__ = ["SQLiteRateLimiter"]
