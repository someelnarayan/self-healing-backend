from collectors.local_collector import LocalCollector
from collectors.ssh_collector import SSHCollector

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

        raise ValueError(
            f"Unknown target type: {target_type}"
        )