from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime


class KnowledgeBase:

    def __init__(self, db_path: str = "knowledge.db"):
        if db_path == ":memory:":
            db_path = ":memory:"

        self._lock = threading.Lock()
        self._cooldowns = {}

        self.db_path = self._normalize_db_path(db_path)

        uri_mode = self.db_path.startswith("file:")

        self._connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            uri=uri_mode
        )

        self._init_db()

    def _normalize_db_path(self, db_path: str) -> str:
        if db_path == ":memory:":
            return f"file:kb_{uuid.uuid4().hex}?mode=memory&cache=shared"

        return db_path

    @contextmanager
    def _conn(self):
        try:
            yield self._connection
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _init_db(self):
        with self._lock, self._conn() as conn:

            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    target_name TEXT,
                    action TEXT,
                    success INTEGER,
                    error_msg TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS anomaly_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    target_name TEXT,
                    anomaly_type TEXT,
                    severity TEXT,
                    metric_value REAL,
                    context TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    target_name TEXT,
                    cpu_pct REAL,
                    ram_pct REAL,
                    response_ms INTEGER,
                    health_ok INTEGER,
                    error_count INTEGER
                )
            """)

    def summary(self):
        return {
            "status": "ok",
            "message": "System running"
        }

    def write_audit(
        self,
        target_name,
        action,
        success,
        error_msg=None
    ):
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log
                (ts, target_name, action, success, error_msg)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    target_name,
                    action,
                    int(success),
                    error_msg
                )
            )

    def write_anomaly(
        self,
        target_name,
        anomaly_type,
        severity,
        metric_value,
        context
    ):
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO anomaly_log
                (
                    ts,
                    target_name,
                    anomaly_type,
                    severity,
                    metric_value,
                    context
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    target_name,
                    anomaly_type,
                    severity,
                    metric_value,
                    context
                )
            )

    def write_signal(
        self,
        target_name,
        cpu_pct,
        ram_pct,
        response_ms,
        health_ok,
        error_count,
    ):
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO signal_log
                (
                    ts,
                    target_name,
                    cpu_pct,
                    ram_pct,
                    response_ms,
                    health_ok,
                    error_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    target_name,
                    cpu_pct,
                    ram_pct,
                    response_ms,
                    int(health_ok),
                    error_count,
                )
            )

    def set_cooldown(self, target, seconds=30):
        self._cooldowns[target] = time.time() + seconds

    def is_on_cooldown(self, target):
        return self._cooldowns.get(target, 0) > time.time()

    def _now(self):
        return datetime.utcnow().isoformat()