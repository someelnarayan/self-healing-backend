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
    - Host CPU / RAM for normal local targets
    - Docker container CPU / RAM / memory for container-backed targets

    Important behavior:
    - On first log read, it jumps to EOF so old historical log lines
      do not trigger false anomalies.
    - Docker stats parsing is defensive, so missing fields do not crash monitoring.
    """

    def __init__(self, target: Target):
        self.target = target

        # None = log not initialized yet
        self._log_pos: int | None = None

        # Reuse docker client for container-backed targets
        self._docker_client = None
        if getattr(self.target, "container_name", ""):
            try:
                self._docker_client = docker.from_env()
            except Exception as e:
                print(
                    f"[Monitor] Docker client init failed for {self.target.name}: {e}",
                    flush=True,
                )
                self._docker_client = None

    def collect(self) -> dict:
        healthy, response_ms = _collect_http(self.target)
        error_count = _collect_logs(self)

        # ---------------------------------------------------------
        # Resource collection strategy
        # ---------------------------------------------------------
        # If this target has a container_name, collect container-scoped
        # CPU / RAM / memory from Docker.
        # Otherwise collect host CPU / RAM using psutil.
        # ---------------------------------------------------------
        if getattr(self.target, "container_name", ""):
            resource_stats = _collect_container(
                self._docker_client,
                self.target.container_name,
            )
        else:
            cpu_pct, ram_pct = _collect_system()
            resource_stats = {
                "cpu_pct": cpu_pct,
                "ram_pct": ram_pct,
                "memory_mb": 0.0,
                "memory_limit_mb": 0.0,
                "disk_pct": 0.0,
            }

        return {
            "healthy": healthy,
            "response_ms": response_ms,
            "error_count": error_count,
            **resource_stats,
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
    Used only for non-container local targets.
    """
    cpu_pct = psutil.cpu_percent(interval=1)
    ram_pct = psutil.virtual_memory().percent
    return cpu_pct, ram_pct


def _collect_container(
    docker_client,
    container_name: str,
) -> dict:
    """
    Collect Docker container CPU / RAM / memory safely.

    Returns:
        {
            "cpu_pct": float,
            "ram_pct": float,
            "memory_mb": float,
            "memory_limit_mb": float,
            "disk_pct": float
        }

    Notes:
    - CPU is computed using Docker cpu_stats + precpu_stats deltas
    - RAM % is container memory usage / container memory limit
    - memory_mb is effective container memory usage in MB
    - memory_limit_mb is included for debugging / observability
    - disk_pct is left 0.0 for now; disk anomaly will be added later
    """
    if docker_client is None:
        return {
            "cpu_pct": 0.0,
            "ram_pct": 0.0,
            "memory_mb": 0.0,
            "memory_limit_mb": 0.0,
            "disk_pct": 0.0,
        }

    try:
        container = docker_client.containers.get(container_name)
        stats = container.stats(stream=False) or {}

        # ---------------------------------------------------------
        # CPU calculation
        # ---------------------------------------------------------
        cpu_stats = stats.get("cpu_stats", {}) or {}
        precpu_stats = stats.get("precpu_stats", {}) or {}

        current_total = (
            cpu_stats.get("cpu_usage", {}) or {}
        ).get("total_usage", 0)

        previous_total = (
            precpu_stats.get("cpu_usage", {}) or {}
        ).get("total_usage", 0)

        current_system = cpu_stats.get("system_cpu_usage", 0)
        previous_system = precpu_stats.get("system_cpu_usage", 0)

        cpu_delta = current_total - previous_total
        system_delta = current_system - previous_system

        online_cpus = cpu_stats.get("online_cpus", 1) or 1

        cpu_pct = 0.0
        if cpu_delta > 0 and system_delta > 0:
            cpu_pct = (cpu_delta / system_delta) * online_cpus * 100.0

        # ---------------------------------------------------------
        # Memory calculation
        # ---------------------------------------------------------
        memory_stats = stats.get("memory_stats", {}) or {}

        raw_usage = memory_stats.get("usage", 0)

        stats_stats = memory_stats.get("stats", {}) or {}
        cache = (
            stats_stats.get("cache")
            or stats_stats.get("inactive_file")
            or 0
        )

        # Never go negative
        effective_usage = max(raw_usage - cache, 0)

        limit = memory_stats.get("limit", 0)

        memory_mb = effective_usage / (1024 * 1024)
        memory_limit_mb = limit / (1024 * 1024) if limit else 0.0

        ram_pct = 0.0
        if limit > 0:
            ram_pct = (effective_usage / limit) * 100.0

        return {
            "cpu_pct": round(cpu_pct, 2),
            "ram_pct": round(ram_pct, 2),
            "memory_mb": round(memory_mb, 2),
            "memory_limit_mb": round(memory_limit_mb, 2),
            "disk_pct": 0.0,
        }

    except docker.errors.NotFound:
        print(
            f"[Monitor] Container not found: {container_name}",
            flush=True,
        )
        return {
            "cpu_pct": 0.0,
            "ram_pct": 0.0,
            "memory_mb": 0.0,
            "memory_limit_mb": 0.0,
            "disk_pct": 0.0,
        }

    except Exception as e:
        print(
            f"[Monitor] Container stats error for {container_name}: {e}",
            flush=True,
        )
        return {
            "cpu_pct": 0.0,
            "ram_pct": 0.0,
            "memory_mb": 0.0,
            "memory_limit_mb": 0.0,
            "disk_pct": 0.0,
        }