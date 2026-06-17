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

import re
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict

import docker
import httpx
import psutil

from config import AppConfig, Target
from knowledge import KnowledgeBase


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

        self._log_pos = 0
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
# Collectors
# ------------------------------------------------------------------

def _collect_http(
    target: Target,
) -> tuple[bool, int]:

    try:

        response = httpx.get(
            target.health_url,
            timeout=5.0,
        )

        response_ms = int(
            response.elapsed.total_seconds()
            * 1000
        )

        return (
            response.status_code == 200,
            response_ms,
        )

    except Exception as e:

        print(
            f"[Monitor] Health check failed "
            f"for {target.name}: {e}",
            flush=True,
        )

        return False, 9999


def _collect_logs(
    state: TargetState,
) -> int:

    patterns = re.compile(
        r"ERROR|OOM|Exception|Traceback|500|OutOfMemory",
        re.IGNORECASE,
    )

    count = 0

    try:

        with open(
            state.target.log_path,
            "r",
            errors="replace",
        ) as f:

            f.seek(state._log_pos)

            for line in f:

                if patterns.search(line):
                    count += 1

            state._log_pos = f.tell()

    except FileNotFoundError:

        print(
            f"[Monitor] Log file not found: "
            f"{state.target.log_path}",
            flush=True,
        )

    return count


def _collect_system() -> tuple[float, float]:

    cpu_pct = psutil.cpu_percent(
        interval=1
    )

    ram_pct = (
        psutil.virtual_memory().percent
    )

    return cpu_pct, ram_pct


def _collect_container(
    container_name: str,
):

    try:

        client = docker.from_env()

        container = client.containers.get(
            container_name
        )

        stats = container.stats(
            stream=False
        )

        memory_usage_mb = (
            stats["memory_stats"]["usage"]
            / (1024 * 1024)
        )

        return {
            "memory_mb":
            round(memory_usage_mb, 2)
        }

    except Exception as e:

        print(
            f"[Monitor] Container stats error: {e}",
            flush=True,
        )

        return {
            "memory_mb": 0
        }


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

        results = {}
        errors = {}

        def run(
            key,
            fn,
            *args,
        ):

            try:

                results[key] = fn(*args)

            except Exception as e:

                errors[key] = e

        state = self._states[target.name]

        threads = [
            threading.Thread(
                target=run,
                args=(
                    "http",
                    _collect_http,
                    target,
                ),
            ),
            threading.Thread(
                target=run,
                args=(
                    "logs",
                    _collect_logs,
                    state,
                ),
            ),
            threading.Thread(
                target=run,
                args=(
                    "sys",
                    _collect_system,
                ),
            ),
            threading.Thread(
                target=run,
                args=(
                    "container",
                    _collect_container,
                    target.container_name,
                ),
            ),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=10)

        health_ok, response_ms = results.get(
            "http",
            (False, 9999),
        )

        error_count = results.get(
            "logs",
            0,
        )

        cpu_pct, ram_pct = results.get(
            "sys",
            (0.0, 0.0),
        )

        container_stats = results.get(
            "container",
            {},
        )

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