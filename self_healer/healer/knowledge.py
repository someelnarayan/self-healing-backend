"""
knowledge.py  ·  Knowledge Base (K in MAPE-K)
SQLite-backed shared store for:
  - signal ring buffer (flushed every 60 s)
  - anomaly events
  - audit log of actions taken
  - cooldown timers per (component, action_type)

All modules READ from and WRITE to this store.
No module calls another module — they talk through Knowledge.
"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class KnowledgeBase:
    def summary(self):
        return {
            "status": "ok",
            "message": "System running"
        }
    
    
    def __init__(self, db_path: str = "/tmp/knowledge.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    # ── Connection helper ──────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── Schema ─────────────────────────────────────────────────────────────────

    def _init_db(self):
        with self._lock, self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS signals (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_name TEXT    NOT NULL,
                    ts          TEXT    NOT NULL,
                    cpu_pct     REAL,
                    ram_pct     REAL,
                    response_ms INTEGER,
                    health_ok   INTEGER,
                    error_count INTEGER
                );

                CREATE TABLE IF NOT EXISTS anomalies (
                    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts                  TEXT    NOT NULL,
                    target_name         TEXT    NOT NULL,
                    anomaly_type        TEXT    NOT NULL,
                    severity            TEXT    NOT NULL,
                    metric_value        REAL,
                    context             TEXT
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts              TEXT    NOT NULL,
                    target_name     TEXT    NOT NULL,
                    anomaly_type    TEXT    NOT NULL,
                    action          TEXT    NOT NULL,
                    success         INTEGER NOT NULL,
                    duration_ms     INTEGER,
                    error_msg       TEXT,
                    dry_run         INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS cooldowns (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_name     TEXT NOT NULL,
                    action_type     TEXT NOT NULL,
                    last_fired_ts   TEXT NOT NULL,
                    UNIQUE(target_name, action_type)
                );
            """)

    # ── Signals ────────────────────────────────────────────────────────────────

    def write_signal(self, target_name: str, cpu_pct: float, ram_pct: float,
                     response_ms: int, health_ok: bool, error_count: int):
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT INTO signals
                   (target_name, ts, cpu_pct, ram_pct, response_ms, health_ok, error_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (target_name, _now(), cpu_pct, ram_pct, response_ms,
                 int(health_ok), error_count)
            )

    def recent_signals(self, target_name: str, n: int = 10) -> List[Dict]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """SELECT * FROM signals WHERE target_name=?
                   ORDER BY id DESC LIMIT ?""",
                (target_name, n)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Anomalies ──────────────────────────────────────────────────────────────

    def write_anomaly(self, target_name: str, anomaly_type: str,
                      severity: str, metric_value: float, context: str):
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT INTO anomalies
                   (ts, target_name, anomaly_type, severity, metric_value, context)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (_now(), target_name, anomaly_type, severity, metric_value, context)
            )

    def recent_anomalies(self, limit: int = 50) -> List[Dict]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM anomalies ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Audit log ──────────────────────────────────────────────────────────────

    def write_audit(self, target_name: str, anomaly_type: str, action: str,
                    success: bool, duration_ms: int,
                    error_msg: Optional[str] = None, dry_run: bool = False):
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (ts, target_name, anomaly_type, action, success,
                    duration_ms, error_msg, dry_run)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (_now(), target_name, anomaly_type, action,
                 int(success), duration_ms, error_msg, int(dry_run))
            )

    def recent_actions(self, limit: int = 50) -> List[Dict]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Cooldowns ──────────────────────────────────────────────────────────────

    def is_on_cooldown(self, target_name: str, action_type: str,
                       cooldown_minutes: int) -> bool:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                """SELECT last_fired_ts FROM cooldowns
                   WHERE target_name=? AND action_type=?""",
                (target_name, action_type)
            ).fetchone()
            if not row:
                return False
            last_ts = datetime.fromisoformat(row[0])
            elapsed_mins = (datetime.utcnow() - last_ts).total_seconds() / 60
            return elapsed_mins < cooldown_minutes

    def mark_cooldown(self, target_name: str, action_type: str):
        with self._lock, self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO cooldowns
                   (target_name, action_type, last_fired_ts)
                   VALUES (?, ?, ?)""",
                (target_name, action_type, _now())
            )


def _now() -> str:
    """ISO format timestamp."""
    return datetime.utcnow().isoformat()