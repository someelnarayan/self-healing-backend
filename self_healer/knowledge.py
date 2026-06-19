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
        self._active_incidents = {}

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

                    memory_mb REAL,
                    disk_pct REAL,

                    ssh_status TEXT,

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

        memory_mb=0,
        disk_pct=0,
        ssh_status="unknown",

        response_ms=0,
        health_ok=True,
        error_count=0,
    ):

        with self._lock, self._conn() as conn:

            conn.execute(
                """
                INSERT INTO signal_log (
                    ts,
                    target_name,

                    cpu_pct,
                    ram_pct,

                    memory_mb,
                    disk_pct,
                    ssh_status,

                    response_ms,
                    health_ok,
                    error_count
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._now(),
                    target_name,

                    cpu_pct,
                    ram_pct,

                    memory_mb,
                    disk_pct,
                    ssh_status,

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

    # ------------------------------------------------------------
    # Read methods (used by the FastAPI /signals, /anomalies,
    # /audit endpoints for the React dashboard)
    # ------------------------------------------------------------

    def get_signals(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ):

        query = """
            SELECT
                id,
                ts,
                target_name,

                cpu_pct,
                ram_pct,

                memory_mb,
                disk_pct,
                ssh_status,

                response_ms,
                health_ok,
                error_count
            FROM signal_log
        """
        params: list = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": r[0],
                "ts": r[1],
                "target_name": r[2],

                "cpu_pct": r[3],
                "ram_pct": r[4],

                "memory_mb": r[5],
                "disk_pct": r[6],
                "ssh_status": r[7],

                "response_ms": r[8],
                "health_ok": bool(r[9]),
                "error_count": r[10],
            }
            for r in rows
        ]

    def get_anomalies(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ):

        query = """
            SELECT id, ts, target_name, anomaly_type,
                   severity, metric_value, context
            FROM anomaly_log
        """
        params: list = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": r[0],
                "ts": r[1],
                "target_name": r[2],
                "anomaly_type": r[3],
                "severity": r[4],
                "metric_value": r[5],
                "context": r[6],
            }
            for r in rows
        ]

    def get_audit(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ):

        query = """
            SELECT id, ts, target_name, anomaly_type,
                   action, success, duration_ms, error_msg
            FROM audit_log
        """
        params: list = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": r[0],
                "ts": r[1],
                "target_name": r[2],
                "anomaly_type": r[3],
                "action": r[4],
                "success": bool(r[5]),
                "duration_ms": r[6],
                "error_msg": r[7],
            }
            for r in rows
        ]

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
    def incident_exists(
        self,
        target_name: str,
        anomaly_type: str,
    ) -> bool:

        key = (
            target_name,
            anomaly_type,
        )

        return key in self._active_incidents


    def create_incident(
        self,
        target_name: str,
        anomaly_type: str,
    ):

        key = (
            target_name,
            anomaly_type,
        )

        self._active_incidents[key] = {
            "status": "OPEN",
            "created_at": time.time(),
        }


    def resolve_incident(
        self,
        target_name: str,
        anomaly_type: str,
    ):

        key = (
        target_name,
        anomaly_type,
        )

        self._active_incidents.pop(
            key,
            None,
    )

    @staticmethod
    def _now() -> str:

        return datetime.utcnow().isoformat()
    

    def update_incident_status(
        self,
        target_name: str,
        anomaly_type: str,
        status: str,
    ):

        key = (
            target_name,
            anomaly_type,
        )

        if key in self._active_incidents:

            self._active_incidents[key][
                "status"
            ] = status
    