from __future__ import annotations

import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime


class KnowledgeBase:

    def __init__(self, db_path: str = "/tmp/knowledge.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._cooldowns = {}
        self._init_db()

    # DB connection
    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # DB init
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

    # summary
    def summary(self):
        return {
            "status": "ok",
            "message": "System running"
        }

    # audit log
    def write_audit(self, target_name, action, success, error_msg=None):
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (ts, target_name, action, success, error_msg) VALUES (?, ?, ?, ?, ?)",
                (self._now(), target_name, action, int(success), error_msg)
            )

    # cooldown
    def set_cooldown(self, target, seconds=30):
        self._cooldowns[target] = time.time() + seconds

    def is_on_cooldown(self, target):
        return self._cooldowns.get(target, 0) > time.time()

    def _now(self):
        return datetime.utcnow().isoformat()