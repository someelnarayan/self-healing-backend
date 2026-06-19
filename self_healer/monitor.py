"""
monitor.py  ·  Monitor (M in MAPE-K)

Runs three collectors in parallel threads every N seconds:

1. HTTP health collector
   - Hits /health
   - Records status and response time

2. Log tail collector
   - Reads new log lines
   - Counts errors and exceptions

3. System metrics collector
   - CPU %
   - RAM %

Monitor only collects data.
It NEVER makes decisions.
Analyzer is responsible for anomaly detection.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict


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
    cpu_pct: float = 0.0
    ram_pct: float = 0.0
    response_ms: int = 0
    health_ok: bool = True
    error_count: int = 0


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
        self.ring: Deque[Signal] = deque(
            maxlen=ring_size
        )
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
    ) -> list:

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

        self._states: Dict[
            str,
            TargetState
        ] = {
            target.name: TargetState(target)
            for target in config.targets
        }

        self.collectors = {
            target.name: CollectorFactory.create(target)
            for target in config.targets
        }

        self._stop_event = threading.Event()

    def get_ring(
        self,
        target_name: str,
    ) -> TargetState:

        return self._states[target_name]

    def poll_once(
        self,
        target: Target,
    ) -> Signal:

        

        state = self._states[target.name]
        collector = self.collectors[target.name]

        metrics = collector.collect()
        if "ssh_status" in metrics:

            print(
                f"[Monitor] SSH Status = "
                f"{metrics['ssh_status']}",
                flush=True,
            )

        health_ok = metrics["healthy"]

        response_ms = metrics["response_ms"]

        error_count = metrics["error_count"]

        cpu_pct = metrics["cpu_pct"]

        ram_pct = metrics["ram_pct"]

        container_stats = {
            "memory_mb": metrics.get(
                "memory_mb",
                0,
        )
    }

        signal = Signal(
            ts=datetime.utcnow(),
            target_name=target.name,
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            response_ms=response_ms,
            health_ok=health_ok,
            error_count=error_count,
        )

        print(
            f"[Monitor] {target.name} | "
            f"health={health_ok} | "
            f"response_ms={response_ms} | "
            f"cpu={cpu_pct:.1f}% | "
            f"ram={ram_pct:.1f}% | "
            f"container_mem="
            f"{container_stats.get('memory_mb', 0)}MB | "
            f"errors={error_count}",
            flush=True,
        )

        state.push(signal)

        self.kb.write_signal(
            target_name=target.name,
            cpu_pct=cpu_pct,
            ram_pct=ram_pct,
            response_ms=response_ms,
            health_ok=health_ok,
            error_count=error_count,
        )

        return signal

    def run_loop(self):

        while not self._stop_event.is_set():

            for target in self.config.targets:

                try:

                    self.poll_once(target)

                except Exception as e:

                    print(
                        f"[Monitor] Error polling "
                        f"{target.name}: {e}",
                        flush=True,
                    )

            self._stop_event.wait(
                timeout=min(
                    target.poll_interval_seconds
                    for target in self.config.targets
                )
            )

    def stop(self):

        self._stop_event.set()