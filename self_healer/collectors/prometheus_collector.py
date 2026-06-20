from collectors.base_collector import BaseCollector
import requests


class PrometheusCollector(BaseCollector):
    def __init__(self, target):
        self.target = target
        self.url = getattr(
            target,
            "prometheus_url",
            "http://prometheus:9090"
        ).rstrip("/")

    def _query(self, promql: str):
        """
        Runs an instant Prometheus query and returns the first numeric result,
        or None if the metric is missing / query fails.
        """
        try:
            response = requests.get(
                f"{self.url}/api/v1/query",
                params={"query": promql},
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            if data.get("status") != "success":
                return None

            result = data.get("data", {}).get("result", [])
            if not result:
                return None

            return float(result[0]["value"][1])

        except Exception:
            return None

    def collect(self):
        try:
            # -------------------------------------------------
            # 1) SYSTEM METRICS FROM NODE-EXPORTER
            # -------------------------------------------------

            # CPU usage %
            cpu_query = """
            100 - (
              avg(rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100
            )
            """
            cpu_pct = self._query(cpu_query)

            # Memory usage
            total_mem = self._query("node_memory_MemTotal_bytes")
            avail_mem = self._query("node_memory_MemAvailable_bytes")

            if total_mem is not None and avail_mem is not None and total_mem > 0:
                used_mem = total_mem - avail_mem
                ram_pct = (used_mem / total_mem) * 100
                memory_mb = used_mem / (1024 * 1024)
            else:
                ram_pct = 0
                memory_mb = 0

            # -------------------------------------------------
            # 2) BOOKSHOP APP METRICS FROM PROMETHEUS
            # -------------------------------------------------
            #
            # These assume Prometheus is scraping:
            #   job="bookshop"
            #
            # The FastAPI instrumentator usually exposes request duration metrics.
            # We'll use those to derive request rate and average latency.
            #
            # NOTE:
            # Metric names can vary slightly by version. The queries below are written
            # for the common prometheus-fastapi-instrumentator naming pattern:
            #
            #   http_request_duration_seconds_count
            #   http_request_duration_seconds_sum
            #
            # If your exact metric names differ, we’ll tweak just these 3 queries.
            #

            # Requests per second over last 1 minute
            request_rate_query = """
            sum(rate(http_request_duration_seconds_count{job="bookshop"}[1m]))
            """
            request_rate = self._query(request_rate_query)

            # Approximate "error count" = rate of 5xx responses * 60
            # If no 5xx labels/metrics exist yet, this may return None -> fallback 0.
            error_rate_query = """
            sum(rate(http_request_duration_seconds_count{job="bookshop",status=~"5.."}[1m]))
            """
            error_rate = self._query(error_rate_query)

            # Average latency in milliseconds
            avg_latency_query = """
            (
              sum(rate(http_request_duration_seconds_sum{job="bookshop"}[1m]))
              /
              sum(rate(http_request_duration_seconds_count{job="bookshop"}[1m]))
            ) * 1000
            """
            avg_latency_ms = self._query(avg_latency_query)

            # Convert per-second 5xx rate into an approximate count over 1 minute
            # so it fits your existing "error_count" style better.
            error_count = int(round((error_rate or 0) * 60))

            # -------------------------------------------------
            # 3) HEALTH DECISION
            # -------------------------------------------------
            # We consider Prometheus target healthy if we can at least fetch CPU.
            healthy = cpu_pct is not None

            # -------------------------------------------------
            # 4) RETURN SIGNAL PAYLOAD
            # -------------------------------------------------
            #
            # Keep the existing keys your monitor/analyzer already expects:
            #   healthy, response_ms, error_count, cpu_pct, ram_pct, memory_mb
            #
            # Add extra Prometheus/Bookshop fields too.
            #
            return {
                "healthy": healthy,

                # For Prometheus target, response_ms will represent Bookshop avg latency
                # if available, otherwise 0.
                "response_ms": round(avg_latency_ms or 0, 2),

                # Error count derived from Bookshop 5xx rate
                "error_count": error_count if healthy else 1,

                # System metrics
                "cpu_pct": round(cpu_pct or 0, 2),
                "ram_pct": round(ram_pct, 2),
                "memory_mb": round(memory_mb, 2),

                # Extra Bookshop app metrics
                "request_rate": round(request_rate or 0, 4),
                "avg_latency_ms": round(avg_latency_ms or 0, 2),
                "bookshop_error_count": error_count,
            }

        except Exception:
            return {
                "healthy": False,
                "response_ms": 0,
                "error_count": 1,
                "cpu_pct": 0,
                "ram_pct": 0,
                "memory_mb": 0,
                "request_rate": 0,
                "avg_latency_ms": 0,
                "bookshop_error_count": 0,
            }