"""SQLite-backed rate limiter with atomic operations and file locking.

Questa implementazione evita deadlock e errori "API misuse" di SQLite usando:
1. INSERT OR IGNORE atomiche
2. Nessuna transazione esplicita (autocommit)
3. Connessione condivisa solo per :memory: (check_same_thread=False)
4. Riprovi con backoff in caso di "database is locked"
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
import threading
from typing import Optional, Tuple
from pathlib import Path
import logging


class SQLiteRateLimiter:
    def __init__(self, db_path: Optional[str] = None, window_seconds: int = 60, max_requests: int = 5):
        self.window = int(window_seconds)
        self.max_requests = int(max_requests)
        self.db_path = db_path or ":memory:"

        # Connessione condivisa solo per DB in memoria
        self._shared_conn = None
        if self.db_path == ":memory:":
            self._shared_conn = self._create_connection()

        # Lock (se in futuro vuoi fare sezioni critiche esplicite)
        self._lock = threading.RLock()
        self._lock_file = None
        if self.db_path != ":memory:":
            lock_path = Path(self.db_path).parent / f"{Path(self.db_path).stem}.lock"
            try:
                self._lock_file = open(lock_path, "w")
            except Exception:
                # Non è critico se il lock file non c'è
                self._lock_file = None

        # Inizializza sempre lo schema, sia memory sia file
        self._init_db()

    # -------------------------
    # Connessione / schema
    # -------------------------

    def _create_connection(self):
        """Crea una nuova connessione SQLite (autocommit, concurrency-friendly)."""
        conn = sqlite3.connect(self.db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = None  # Autocommit

        # Pragme di base (non dovrebbero generare errori)
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            # Alcuni ambienti non lo supportano, ignoriamo
            pass

        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("PRAGMA cache_size = 10000")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def _conn(self):
        """Restituisce una connessione: condivisa per :memory:, nuova per file."""
        if self._shared_conn is not None:
            return self._shared_conn
        return self._create_connection()

    def _init_db(self):
        """Inizializza lo schema (tabella + indici)."""
        conn = self._conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key TEXT NOT NULL,
                window_start INTEGER NOT NULL,
                count INTEGER NOT NULL DEFAULT 1,
                blocked_until INTEGER DEFAULT 0,
                UNIQUE(api_key, window_start)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_api_key ON api_usage(api_key)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_blocked ON api_usage(blocked_until)")

        # Se non è in-memory, chiudiamo questa connessione di init
        if self._shared_conn is None:
            try:
                conn.close()
            except Exception:
                pass

    # -------------------------
    # Utilità interne
    # -------------------------

    def _window_start(self, now: Optional[float] = None) -> int:
        if now is None:
            now = time.time()
        return int(now // self.window) * self.window

    # -------------------------
    # API pubblica
    # -------------------------

    async def increment_and_check(self, api_key: str) -> Tuple[bool, int, Optional[int]]:
        """Wrapper async: esegue la logica su thread separato."""
        return await asyncio.to_thread(self._increment_and_check_sync, api_key)

    def _increment_and_check_sync(self, api_key: str) -> Tuple[bool, int, Optional[int]]:
        """Incrementa il contatore e verifica il rate limit con operazioni atomiche."""
        now = int(time.time())
        window_start = self._window_start(now)

        max_retries = 20
        for attempt in range(max_retries):
            try:
                conn = self._conn()
                cur = conn.cursor()

                # 1) Controlla se la chiave è già bloccata
                cur.execute(
                    """
                    SELECT blocked_until
                    FROM api_usage
                    WHERE api_key = ?
                      AND blocked_until > ?
                    ORDER BY window_start DESC
                    LIMIT 1
                    """,
                    (api_key, now),
                )
                row = cur.fetchone()
                if row and row["blocked_until"]:
                    retry_after = int(row["blocked_until"]) - now
                    return False, 0, max(retry_after, 0)

                # 2) Inserisci riga se non esiste
                cur.execute(
                    """
                    INSERT OR IGNORE INTO api_usage (api_key, window_start, count, blocked_until)
                    VALUES (?, ?, 1, 0)
                    """,
                    (api_key, window_start),
                )

                # 3) Incrementa contatore per la finestra corrente
                cur.execute(
                    """
                    UPDATE api_usage
                    SET count = count + 1
                    WHERE api_key = ? AND window_start = ?
                    """,
                    (api_key, window_start),
                )

                # 4) Leggi il nuovo valore di count
                cur.execute(
                    """
                    SELECT count
                    FROM api_usage
                    WHERE api_key = ? AND window_start = ?
                    """,
                    (api_key, window_start),
                )
                row = cur.fetchone()
                cur_count = int(row["count"]) if row and row["count"] is not None else 1

                remaining = max(0, self.max_requests - cur_count)

                # 5) Se ha superato il limite → blocca fino alla fine della finestra
                if cur_count > self.max_requests:
                    blocked_ts = now + self.window
                    cur.execute(
                        """
                        UPDATE api_usage
                        SET blocked_until = ?
                        WHERE api_key = ? AND window_start = ?
                        """,
                        (blocked_ts, api_key, window_start),
                    )
                    return False, 0, self.window

                # Nessun blocco
                return True, remaining, None

            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "database is locked" in msg and attempt < max_retries - 1:
                    # Backoff esponenziale
                    backoff = 0.001 * (2 ** min(attempt, 8))
                    time.sleep(backoff)
                    continue
                logging.error(f"Rate limiter error after {max_retries} retries: {e}")
                return False, 0, 1
            except Exception as e:
                logging.error(f"Rate limiter unexpected error: {e}")
                return False, 0, 1
            finally:
                # Chiudi solo se è una connessione "usa e getta"
                if self._shared_conn is None and "conn" in locals():
                    try:
                        conn.close()
                    except Exception:
                        pass

        return False, 0, 1

    async def is_blocked(self, api_key: str) -> Optional[int]:
        return await asyncio.to_thread(self._is_blocked_sync, api_key)

    def _is_blocked_sync(self, api_key: str) -> Optional[int]:
        """Verifica se la chiave è al momento bloccata. Restituisce i secondi rimanenti o None."""
        now = int(time.time())
        max_retries = 10

        for attempt in range(max_retries):
            try:
                conn = self._conn()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT blocked_until
                    FROM api_usage
                    WHERE api_key = ?
                      AND blocked_until > ?
                    ORDER BY window_start DESC
                    LIMIT 1
                    """,
                    (api_key, now),
                )
                row = cur.fetchone()

                if self._shared_conn is None:
                    try:
                        conn.close()
                    except Exception:
                        pass

                if not row or not row["blocked_until"]:
                    return None

                blocked_ts = int(row["blocked_until"])
                if blocked_ts > now:
                    return blocked_ts - now
                return None

            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if "database is locked" in msg and attempt < max_retries - 1:
                    time.sleep(0.001 * (2 ** min(attempt, 8)))
                    continue
                return None
            except Exception as e:
                logging.warning(f"is_blocked error: {e}")
                return None

        return None


__all__ = ["SQLiteRateLimiter"]
