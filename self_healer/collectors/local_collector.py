from __future__ import annotations

import re
from pathlib import Path

import docker
import httpx
import psutil

from config import Target
from collectors.base_collector import BaseCollector


class LocalCollector(BaseCollector):
    """
    Collector for local / docker-based targets such as bookshop.

    Collects:
    - HTTP health + response time
    - New log errors since last poll
    - Host CPU / RAM
    - Docker container memory usage (if container_name configured)

    Important behavior:
    - On first log read, it jumps to EOF so old historical log lines
      do not trigger false anomalies.
    - Docker stats parsing is defensive, so missing fields do not crash monitoring.
    """

    def __init__(self, target: Target):
        self.target = target

        # None = log not initialized yet
        self._log_pos: int | None = None

    def collect(self) -> dict:
        healthy, response_ms = _collect_http(self.target)

        error_count = _collect_logs(self)

        cpu_pct, ram_pct = _collect_system()

        container_stats = {}
        if getattr(self.target, "container_name", None):
            container_stats = _collect_container(
                self.target.container_name
            )

        return {
            "healthy": healthy,
            "response_ms": response_ms,
            "error_count": error_count,
            "cpu_pct": cpu_pct,
            "ram_pct": ram_pct,
            **container_stats,
        }


def _collect_http(target: Target) -> tuple[bool, int]:
    """
    Perform HTTP health check for local service.
    Returns:
        (healthy, response_ms)
    """
    if not target.health_url:
        return True, 0

    try:
        response = httpx.get(
            target.health_url,
            timeout=5.0,
        )

        response_ms = int(
            response.elapsed.total_seconds() * 1000
        )

        return response.status_code == 200, response_ms

    except Exception as e:
        print(
            f"[Monitor] Health check failed for {target.name}: {e}",
            flush=True,
        )
        return False, 9999


def _collect_logs(collector: LocalCollector) -> int:
    """
    Count NEW error lines appended to the log since the previous poll.

    First poll behavior:
    - jump to end of file
    - do not count old historical log lines
    """
    log_path = getattr(collector.target, "log_path", "") or ""
    if not log_path:
        return 0

    path = Path(log_path)

    patterns = re.compile(
        r"ERROR|OOM|Exception|Traceback|500|OutOfMemory",
        re.IGNORECASE,
    )

    count = 0

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            # First ever read → ignore historical log lines
            if collector._log_pos is None:
                f.seek(0, 2)  # EOF
                collector._log_pos = f.tell()
                return 0

            # Handle log truncation / rotation
            f.seek(0, 2)
            file_size = f.tell()

            if collector._log_pos > file_size:
                collector._log_pos = 0

            # Read only newly appended content
            f.seek(collector._log_pos)

            for line in f:
                if patterns.search(line):
                    count += 1

            collector._log_pos = f.tell()

    except FileNotFoundError:
        print(
            f"[Monitor] Log file not found: {collector.target.log_path}",
            flush=True,
        )

    except Exception as e:
        print(
            f"[Monitor] Log collection error for {collector.target.name}: {e}",
            flush=True,
        )

    return count


def _collect_system() -> tuple[float, float]:
    """
    Collect host CPU and RAM as seen from healer runtime.
    """
    cpu_pct = psutil.cpu_percent(interval=1)
    ram_pct = psutil.virtual_memory().percent
    return cpu_pct, ram_pct


def _collect_container(container_name: str) -> dict:
    """
    Collect Docker container memory stats safely.

    Returns:
        {
            "memory_mb": float,
            "disk_pct": 0.0
        }

    Why this version is safer:
    - Some Docker stats payloads may not contain memory_stats["usage"]
    - Some payloads may be partially empty for a moment right after container startup
    - We do not want monitoring to break because of missing keys
    """
    try:
        client = docker.from_env()
        container = client.containers.get(container_name)
        stats = container.stats(stream=False) or {}

        memory_stats = stats.get("memory_stats", {}) or {}

        # Docker sometimes gives:
        # memory_stats = {"usage": ...}
        # sometimes "usage" can be absent momentarily
        raw_usage = memory_stats.get("usage", 0)

        # Optional: subtract cache to get more realistic app memory
        stats_stats = memory_stats.get("stats", {}) or {}
        cache = (
            stats_stats.get("cache")
            or stats_stats.get("inactive_file")
            or 0
        )

        # Never go negative
        effective_usage = max(raw_usage - cache, 0)

        memory_usage_mb = effective_usage / (1024 * 1024)

        return {
            "memory_mb": round(memory_usage_mb, 2),
            "disk_pct": 0.0,
        }

    except docker.errors.NotFound:
        print(
            f"[Monitor] Container not found: {container_name}",
            flush=True,
        )
        return {
            "memory_mb": 0.0,
            "disk_pct": 0.0,
        }

    except Exception as e:
        print(
            f"[Monitor] Container stats error for {container_name}: {e}",
            flush=True,
        )
        return {
            "memory_mb": 0.0,
            "disk_pct": 0.0,
        }