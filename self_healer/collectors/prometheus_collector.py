from collectors.base_collector import BaseCollector
import requests


class PrometheusCollector(BaseCollector):

    def __init__(self, target):
        self.target = target
        self.url = getattr(
            target,
            "url",
            "http://localhost:9090"
        )

    def _query(self, promql):
        try:
            response = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": promql},
                timeout=5
            )

            data = response.json()

            if data["status"] != "success":
                return None

            result = data["data"]["result"]

            if not result:
                return None

            return float(result[0]["value"][1])

        except Exception:
            return None

    def collect(self):

        try:

            cpu_query = """
            100 - (
                avg(
                    rate(node_cpu_seconds_total{mode="idle"}[1m])
                ) * 100
            )
            """

            cpu_pct = self._query(cpu_query)

            total_mem = self._query(
                "node_memory_MemTotal_bytes"
            )

            avail_mem = self._query(
                "node_memory_MemAvailable_bytes"
            )

            if total_mem and avail_mem:
                ram_pct = (
                    (total_mem - avail_mem)
                    / total_mem
                ) * 100

                memory_mb = (
                    total_mem - avail_mem
                ) / (1024 * 1024)

            else:
                ram_pct = 0
                memory_mb = 0

            return {
                "healthy": True,
                "response_ms": 0,
                "error_count": 0,
                "cpu_pct": round(cpu_pct or 0, 2),
                "ram_pct": round(ram_pct, 2),
                "memory_mb": round(memory_mb, 2),
            }

        except Exception:

            return {
                "healthy": False,
                "response_ms": 0,
                "error_count": 1,
                "cpu_pct": 0,
                "ram_pct": 0,
                "memory_mb": 0,
            }