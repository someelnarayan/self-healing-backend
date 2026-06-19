from collectors.base_collector import BaseCollector

import paramiko


class SSHCollector(BaseCollector):

    def __init__(self, target):
        self.target = target

    def _connect(self):

        client = paramiko.SSHClient()

        client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )

        client.connect(
            hostname=self.target.host,
            username=self.target.username,
            key_filename=self.target.ssh_key,
            timeout=10,
        )

        return client

    def collect(self):

        client = self._connect()

        try:

            return {
                "healthy": True,
                "response_ms": 0,
                "error_count": 0,
                "cpu_pct": 0,
                "ram_pct": 0,
                "memory_mb": 0,
            }

        finally:

            client.close()