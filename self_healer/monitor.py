"""
monitor.py  ·  Monitor (M in MAPE-K)
Runs three collectors in parallel threads every N seconds:
  1. HTTP health collector  — hits /health, records status + response time
  2. Log tail collector     — reads new log lines, counts errors/OOM events
  3. System metrics         — uses psutil for CPU %, RAM %

Only collects and writes to KnowledgeBase.
NEVER makes decisions — that is analyzer.py's job.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, Optional

import httpx
import psutil

from config import AppConfig, Target
from knowledge import KnowledgeBase


# ── Signal dataclass (in-memory ring buffer entry) ─────────────────────────────

@dataclass
class Signal:
    ts: datetime
    target_name: str
    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    response_ms: int = 0
    health_ok: bool = True
    error_count: int = 0


# ── Per-target state ───────────────────────────────────────────────────────────

class TargetState:
    def __init__(self, target: Target, ring_size: int = 60):
        self.target = target
        self.ring: Deque[Signal] = deque(maxlen=ring_size)
        self._log_pos: int = 0
        self._lock = threading.Lock()

    def push(self, signal: Signal):
        with self._lock:
            self.ring.append(signal)

    def last_n(self, n: int) -> list:
        with self._lock:
            return list(self.ring)[-n:]


# ── Collectors ─────────────────────────────────────────────────────────────────

def _collect_http(target: Target) -> tuple[bool, int]:
    """Returns (health_ok, response_ms)."""
    try:
        resp = httpx.get(target.health_url, timeout=5.0)
        ms = int(resp.elapsed.total_seconds() * 1000)
        return resp.status_code == 200, ms
    except Exception:
        return False, 9999


def _collect_logs(state: TargetState) -> int:
    """Returns count of error/OOM lines seen since last poll."""
    patterns = re.compile(r"ERROR|OOM|Exception|Traceback|500|OutOfMemory",
                          re.IGNORECASE)
    count = 0
    try:
        with open(state.target.log_path, "r", errors="replace") as f:
            f.seek(state._log_pos)
            for line in f:
                if patterns.search(line):
                    count += 1
            state._log_pos = f.tell()
    except FileNotFoundError:
        pass
    return count


def _collect_system() -> tuple[float, float]:
    """Returns (cpu_pct, ram_pct)."""
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    return cpu, ram


# ── Monitor ────────────────────────────────────────────────────────────────────

class Monitor:
    def __init__(self, config: AppConfig, kb: KnowledgeBase):
        self.config = config
        self.kb = kb
        self._states: Dict[str, TargetState] = {
            t.name: TargetState(t) for t in config.targets
        }
        self._stop_event = threading.Event()

    def get_ring(self, target_name: str) -> TargetState:
        return self._states[target_name]

    def poll_once(self, target: Target) -> Signal:
        results: Dict = {}
        errors: Dict = {}

        def run(key, fn, *args):
            try:
                results[key] = fn(*args)
            except Exception as e:
                errors[key] = e

        state = self._states[target.name]
        threads = [
            threading.Thread(target=run, args=("http", _collect_http, target)),
            threading.Thread(target=run, args=("logs", _collect_logs, state)),
            threading.Thread(target=run, args=("sys", _collect_system)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        health_ok, response_ms = results.get("http", (False, 9999))
        error_count = results.get("logs", 0)
        cpu_pct, ram_pct = results.get("sys", (0.0, 0.0))

        sig = Signal(
            ts=datetime.utcnow(),
            target_name=target.name,
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            response_ms=response_ms,
            health_ok=health_ok,
            error_count=error_count,
        )
        state.push(sig)
        self.kb.write_signal(
            target.name, cpu_pct, ram_pct, response_ms, health_ok, error_count
        )
        return sig

    def run_loop(self):
        """Background loop — runs until stop() is called."""
        while not self._stop_event.is_set():
            for target in self.config.targets:
                try:
                    self.poll_once(target)
                except Exception as e:
                    print(f"[Monitor] Error polling {target.name}: {e}")
            self._stop_event.wait(
                timeout=min(t.poll_interval_seconds for t in self.config.targets)
            )

    def stop(self):
        self._stop_event.set()