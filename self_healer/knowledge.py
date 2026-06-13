from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime


class KnowledgeBase:

    def __init__(self, db_path: str = "knowledge.db"):

        self._lock = threading.Lock()
        self._cooldowns = {}

        self.db_path = self._normalize_db_path(db_path)

        uri_mode = self.db_path.startswith("file:")

        self._connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            uri=uri_mode,
        )

        self._init_db()

    def _normalize_db_path(self, db_path: str) -> str:

        if db_path == ":memory:":
            return (
                f"file:kb_{uuid.uuid4().hex}"
                f"?mode=memory&cache=shared"
            )

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

            conn.execute(
                """
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
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS anomaly_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    target_name TEXT,
                    anomaly_type TEXT,
                    severity TEXT,
                    metric_value REAL,
                    context TEXT
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    target_name TEXT,
                    anomaly_type TEXT,
                    action TEXT,
                    success INTEGER,
                    duration_ms INTEGER,
                    error_msg TEXT
                )
                """
            )

    def summary(self):

        with self._lock, self._conn() as conn:

            signal_count = conn.execute(
                "SELECT COUNT(*) FROM signal_log"
            ).fetchone()[0]

            anomaly_count = conn.execute(
                "SELECT COUNT(*) FROM anomaly_log"
            ).fetchone()[0]

            audit_count = conn.execute(
                "SELECT COUNT(*) FROM audit_log"
            ).fetchone()[0]

        return {
            "status": "ok",
            "signals": signal_count,
            "anomalies": anomaly_count,
            "audits": audit_count,
        }

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
                INSERT INTO signal_log (
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
                ),
            )

    def write_anomaly(
        self,
        target_name,
        anomaly_type,
        severity,
        metric_value,
        context,
    ):

        with self._lock, self._conn() as conn:

            conn.execute(
                """
                INSERT INTO anomaly_log (
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
                    context,
                ),
            )

    def write_audit(
        self,
        target_name,
        anomaly_type,
        action,
        success,
        duration_ms,
        error_msg=None,
    ):

        with self._lock, self._conn() as conn:

            conn.execute(
                """
                INSERT INTO audit_log (
                    ts,
                    target_name,
                    anomaly_type,
                    action,
                    success,
                    duration_ms,
                    error_msg
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    target_name,
                    anomaly_type,
                    action,
                    int(success),
                    duration_ms,
                    error_msg,
                ),
            )

    def set_cooldown(
        self,
        target_name: str,
        seconds: int = 30,
    ):

        self._cooldowns[target_name] = (
            time.time() + seconds
        )

    def is_on_cooldown(
        self,
        target_name: str,
    ) -> bool:

        return (
            self._cooldowns.get(target_name, 0)
            > time.time()
        )

    def clear_cooldown(
        self,
        target_name: str,
    ):

        self._cooldowns.pop(
            target_name,
            None,
        )

    def get_cooldown_remaining(
        self,
        target_name: str,
    ) -> int:

        expiry = self._cooldowns.get(
            target_name,
            0,
        )

        remaining = int(
            expiry - time.time()
        )

        return max(0, remaining)

    @staticmethod
    def _now() -> str:

        return datetime.utcnow().isoformat()