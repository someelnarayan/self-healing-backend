from config import Target

import re
import docker
import httpx
import psutil


class LocalCollector:

    def __init__(self, target: Target):
        self.target = target
        self._log_pos = 0

    def collect(self):

        healthy, response_ms = _collect_http(
            self.target
        )

        error_count = _collect_logs(
            self
        )

        cpu_pct, ram_pct = _collect_system()

        container_stats = {}

        if getattr(
            self.target,
            "container_name",
            None,
        ):
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
    collector,
) -> int:

    patterns = re.compile(
        r"ERROR|OOM|Exception|Traceback|500|OutOfMemory",
        re.IGNORECASE,
    )

    count = 0

    try:

        with open(
            collector.target.log_path,
            "r",
            errors="replace",
        ) as f:

            f.seek(
                collector._log_pos
            )

            for line in f:

                if patterns.search(line):
                    count += 1

            collector._log_pos = (
                f.tell()
            )

    except FileNotFoundError:

        print(
            f"[Monitor] Log file not found: "
            f"{collector.target.log_path}",
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

        container = (
            client.containers.get(
                container_name
            )
        )

        stats = container.stats(
            stream=False
        )

        memory_usage_mb = (
            stats["memory_stats"]["usage"]
            / (1024 * 1024)
        )

        return {
            "memory_mb": round(
                memory_usage_mb,
                2,
            )
        }

    except Exception as e:

        print(
            f"[Monitor] Container stats error: {e}",
            flush=True,
        )

        return {
            "memory_mb": 0
        }