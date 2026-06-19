from collectors.local_collector import LocalCollector
from collectors.ssh_collector import SSHCollector
from collectors.prometheus_collector import PrometheusCollector

class CollectorFactory:

    @staticmethod
    def create(target):

        target_type = getattr(
            target,
            "type",
            "local",
        )

        if target_type == "local":
            return LocalCollector(target)
        if target_type == "ssh":
            return SSHCollector(target)
        if target_type == "prometheus":
            return PrometheusCollector(target)

        raise ValueError(
            f"Unknown target type: {target_type}"
        )