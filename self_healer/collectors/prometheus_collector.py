from collectors.base_collector import BaseCollector


class PrometheusCollector(BaseCollector):

    def __init__(self, target):
        self.target = target

    def collect(self):

        return {
            "healthy": True,
            "response_ms": 0,
            "error_count": 0,
            "cpu_pct": 0,
            "ram_pct": 0,
            "memory_mb": 0,
        }