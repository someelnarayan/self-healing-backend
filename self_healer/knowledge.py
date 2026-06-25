from __future__ import annotations

import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Optional


class KnowledgeBase:
    def __init__(self, db_path: str = "knowledge.db"):
        self._lock = threading.Lock()

        # cooldown_key -> expiry_timestamp
        self._cooldowns: Dict[str, float] = {}

        # (target_name, anomaly_type) -> incident state
        self._active_incidents: Dict[tuple[str, str], Dict[str, Any]] = {}

        self.db_path = self._normalize_db_path(db_path)

        uri_mode = self.db_path.startswith("file:")

        self._connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            uri=uri_mode,
        )
        self._connection.row_factory = sqlite3.Row

        self._init_db()

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

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

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat()

    # ------------------------------------------------------------
    # Database initialization
    # ------------------------------------------------------------

    def _init_db(self):
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signal_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    cpu_pct REAL DEFAULT 0,
                    ram_pct REAL DEFAULT 0,
                    memory_mb REAL DEFAULT 0,
                    disk_pct REAL DEFAULT 0,
                    ssh_status TEXT DEFAULT 'unknown',
                    response_ms INTEGER DEFAULT 0,
                    health_ok INTEGER DEFAULT 1,
                    error_count INTEGER DEFAULT 0
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS anomaly_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    metric_value REAL DEFAULT 0,
                    context TEXT
                )
                """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    anomaly_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    error_msg TEXT
                )
                """
            )

    # ------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------

    def summary(self) -> dict:
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
            "active_incidents": len(self._active_incidents),
            "active_cooldowns": len(self._cooldowns),
        }

    # ------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------

    def write_signal(
        self,
        target_name: str,
        cpu_pct: float,
        ram_pct: float,
        memory_mb: float = 0.0,
        disk_pct: float = 0.0,
        ssh_status: str = "unknown",
        response_ms: int = 0,
        health_ok: bool = True,
        error_count: int = 0,
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
        target_name: str,
        anomaly_type: str,
        severity: str,
        metric_value: float,
        context: str,
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
        target_name: str,
        anomaly_type: str,
        action: str,
        success: bool,
        duration_ms: int = 0,
        error_msg: str | None = None,
    ):
        """
        Store one executor action result.

        Example:
            kb.write_audit(
                target_name="ssh-test",
                anomaly_type="HIGH_CPU",
                action="cleanup_cpu_stress",
                success=True,
                duration_ms=82,
                error_msg=None,
            )
        """
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
                    int(duration_ms),
                    error_msg,
                ),
            )

    # ------------------------------------------------------------
    # Read methods (used by FastAPI / dashboard endpoints)
    # ------------------------------------------------------------

    def get_signals(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ) -> list[dict]:
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
        params: list[Any] = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row["id"],
                "ts": row["ts"],
                "target_name": row["target_name"],
                "cpu_pct": row["cpu_pct"],
                "ram_pct": row["ram_pct"],
                "memory_mb": row["memory_mb"],
                "disk_pct": row["disk_pct"],
                "ssh_status": row["ssh_status"],
                "response_ms": row["response_ms"],
                "health_ok": bool(row["health_ok"]),
                "error_count": row["error_count"],
            }
            for row in rows
        ]

    def get_anomalies(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT
                id,
                ts,
                target_name,
                anomaly_type,
                severity,
                metric_value,
                context
            FROM anomaly_log
        """
        params: list[Any] = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row["id"],
                "ts": row["ts"],
                "target_name": row["target_name"],
                "anomaly_type": row["anomaly_type"],
                "severity": row["severity"],
                "metric_value": row["metric_value"],
                "context": row["context"],
            }
            for row in rows
        ]

    def get_audit(
        self,
        limit: int = 100,
        target_name: str | None = None,
    ) -> list[dict]:
        query = """
            SELECT
                id,
                ts,
                target_name,
                anomaly_type,
                action,
                success,
                duration_ms,
                error_msg
            FROM audit_log
        """
        params: list[Any] = []

        if target_name:
            query += " WHERE target_name = ?"
            params.append(target_name)

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._lock, self._conn() as conn:
            rows = conn.execute(query, params).fetchall()

        return [
            {
                "id": row["id"],
                "ts": row["ts"],
                "target_name": row["target_name"],
                "anomaly_type": row["anomaly_type"],
                "action": row["action"],
                "success": bool(row["success"]),
                "duration_ms": row["duration_ms"],
                "error_msg": row["error_msg"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------
    # Cooldown management
    # ------------------------------------------------------------

    def set_cooldown(
        self,
        cooldown_key: str,
        seconds: int = 30,
    ):
        self._cooldowns[cooldown_key] = time.time() + seconds

    def is_on_cooldown(
        self,
        cooldown_key: str,
    ) -> bool:
        return self._cooldowns.get(cooldown_key, 0) > time.time()

    def clear_cooldown(
        self,
        cooldown_key: str,
    ):
        self._cooldowns.pop(cooldown_key, None)

    def get_cooldown_remaining(
        self,
        cooldown_key: str,
    ) -> int:
        expiry = self._cooldowns.get(cooldown_key, 0)
        remaining = int(expiry - time.time())
        return max(0, remaining)

    # ------------------------------------------------------------
    # Incident tracking (in-memory for now)
    # ------------------------------------------------------------

    def incident_exists(
        self,
        target_name: str,
        anomaly_type: str,
    ) -> bool:
        return (target_name, anomaly_type) in self._active_incidents

    def create_incident(
        self,
        target_name: str,
        anomaly_type: str,
    ):
        key = (target_name, anomaly_type)
        self._active_incidents[key] = {
            "status": "OPEN",
            "created_at": time.time(),
            "updated_at": time.time(),
        }

    def resolve_incident(
        self,
        target_name: str,
        anomaly_type: str,
    ):
        key = (target_name, anomaly_type)
        self._active_incidents.pop(key, None)

    def update_incident_status(
        self,
        target_name: str,
        anomaly_type: str,
        status: str,
    ):
        key = (target_name, anomaly_type)
        if key in self._active_incidents:
            self._active_incidents[key]["status"] = status
            self._active_incidents[key]["updated_at"] = time.time()

    def get_incident_status(
        self,
        target_name: str,
        anomaly_type: str,
    ) -> Optional[str]:
        key = (target_name, anomaly_type)
        if key not in self._active_incidents:
            return None
        return self._active_incidents[key].get("status")

    def get_active_incidents(self) -> list[dict]:
        results = []

        for (target_name, anomaly_type), data in self._active_incidents.items():
            results.append(
                {
                    "target_name": target_name,
                    "anomaly_type": anomaly_type,
                    "status": data.get("status", "OPEN"),
                    "created_at": data.get("created_at"),
                    "updated_at": data.get("updated_at"),
                }
            )

        return results