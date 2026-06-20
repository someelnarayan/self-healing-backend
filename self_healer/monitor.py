"""
monitor.py · Monitor (M in MAPE-K)

Responsibilities:
- Poll target collectors
- Normalize raw collector output into Signal objects
- Store recent signals in per-target ring buffers
- Persist signals into KnowledgeBase

Monitor only collects data.
It NEVER makes decisions.
Analyzer is responsible for anomaly detection.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, Optional

from config import AppConfig, Target
from knowledge import KnowledgeBase
from collectors.collector_factory import CollectorFactory


# ------------------------------------------------------------------
# Signal
# ------------------------------------------------------------------

@dataclass
class Signal:
    ts: datetime
    target_name: str
    target_id: str

    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    response_ms: int = 0
    health_ok: bool = True
    error_count: int = 0

    # richer signal fields for future anomaly detection
    memory_mb: float = 0.0
    disk_pct: float = 0.0
    ssh_status: str = "unknown"


# ------------------------------------------------------------------
# Target State
# ------------------------------------------------------------------

class TargetState:
    def __init__(
        self,
        target: Target,
        ring_size: int = 60,
    ):
        self.target = target
        self.ring: Deque[Signal] = deque(maxlen=ring_size)
        self._lock = threading.Lock()

    def push(
        self,
        signal: Signal,
    ):
        with self._lock:
            self.ring.append(signal)

    def last_n(
        self,
        n: int,
    ) -> list[Signal]:
        with self._lock:
            return list(self.ring)[-n:]


# ------------------------------------------------------------------
# Monitor
# ------------------------------------------------------------------

class Monitor:
    def __init__(
        self,
        config: AppConfig,
        kb: KnowledgeBase,
    ):
        self.config = config
        self.kb = kb

        # Use target.id as the stable internal key
        self._states: Dict[str, TargetState] = {
            target.id: TargetState(target)
            for target in config.targets
        }

        self.collectors = {
            target.id: CollectorFactory.create(target)
            for target in config.targets
        }

        self._stop_event = threading.Event()

    def _target_key(
        self,
        target: Target,
    ) -> str:
        return target.id

    def get_ring(
        self,
        target_name: str,
    ) -> TargetState:
        """
        Backward-compatible lookup:
        accepts either target.id or target.name
        """
        if target_name in self._states:
            return self._states[target_name]

        for target in self.config.targets:
            if target.name == target_name:
                return self._states[target.id]

        raise KeyError(f"Unknown target ring requested: {target_name}")

    def poll_once(
        self,
        target: Target,
    ) -> Signal:
        target_key = self._target_key(target)
        state = self._states[target_key]
        collector = self.collectors[target_key]

        metrics = collector.collect() or {}

        health_ok = metrics.get("healthy", True)
        response_ms = metrics.get("response_ms", 0)
        error_count = metrics.get("error_count", 0)
        cpu_pct = metrics.get("cpu_pct", 0.0)
        ram_pct = metrics.get("ram_pct", 0.0)

        memory_mb = metrics.get("memory_mb", 0.0)
        disk_pct = metrics.get("disk_pct", 0.0)
        ssh_status = metrics.get("ssh_status", "unknown")

        signal = Signal(
            ts=datetime.utcnow(),
            target_name=target.name,
            target_id=target.id,
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            response_ms=response_ms,
            health_ok=health_ok,
            error_count=error_count,
            memory_mb=memory_mb,
            disk_pct=disk_pct,
            ssh_status=ssh_status,
        )

        print(
            f"[Monitor] {target.name} | "
            f"health={health_ok} | "
            f"response_ms={response_ms} | "
            f"cpu={cpu_pct:.1f}% | "
            f"ram={ram_pct:.1f}% | "
            f"memory={memory_mb}MB | "
            f"disk={disk_pct}% | "
            f"ssh={ssh_status} | "
            f"errors={error_count}",
            flush=True,
        )

        state.push(signal)

        self.kb.write_signal(
            target_name=target.name,
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            memory_mb=memory_mb,
            disk_pct=disk_pct,
            ssh_status=ssh_status,
            response_ms=response_ms,
            health_ok=health_ok,
            error_count=error_count,
        )

        return signal

    def run_loop(self):
        """
        Current simple loop:
        polls every target each cycle, then sleeps for the minimum configured interval.

        Later, this can be upgraded into per-target scheduling.
        """
        if not self.config.targets:
            print("[Monitor] No targets configured", flush=True)
            return

        sleep_seconds = min(
            target.poll_interval_seconds
            for target in self.config.targets
        )

        while not self._stop_event.is_set():
            for target in self.config.targets:
                try:
                    self.poll_once(target)
                except Exception as e:
                    print(
                        f"[Monitor] Error polling {target.name}: {e}",
                        flush=True,
                    )

            self._stop_event.wait(timeout=sleep_seconds)

    def stop(self):
        self._stop_event.set()