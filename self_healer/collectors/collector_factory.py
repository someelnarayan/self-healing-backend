from collectors.local_collector import LocalCollector


class CollectorFactory:

    @staticmethod
    def create(target):

        target_type = target.get("type", "local")

        if target_type == "local":
            return LocalCollector(target)

        raise ValueError(f"Unknown target type: {target_type}")
    from collectors.local_collector import LocalCollector


class CollectorFactory:

    @staticmethod
    def create(target):

        target_type = getattr(
            target,
            "type",
            "local",
        )

        if target_type == "local":
            return LocalCollector()

        raise ValueError(
            f"Unknown target type: {target_type}"
        )