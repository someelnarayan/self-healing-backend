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

            # Hostname

            stdin, stdout, stderr = client.exec_command(
                "hostname"
            )

            hostname = (
                stdout.read()
                .decode()
                .strip()
            )

           # CPU

            stdin, stdout, stderr = client.exec_command(
                "top -bn1 | grep 'Cpu(s)'"
            )

            cpu_output = (
                stdout.read()
                .decode()
                .strip()
            )

            print(
                f"[SSH DEBUG] CPU RAW = {cpu_output}",
                flush=True,
            )

            cpu_pct = 0.0

            for part in cpu_output.split(","):

                part = part.strip()

                if " id" in part:

                    idle = float(
                    part.split()[0]
                    )

                    print(
                        f"[SSH DEBUG] idle={idle}",
                        flush=True,
                    )

                    cpu_pct = round(
                    100 - idle,
                    2,
                    )

                    print(
                    f"[SSH DEBUG] cpu_pct={cpu_pct}",
                    flush=True,
                )

                break

            # RAM

            stdin, stdout, stderr = client.exec_command(
                "free -m"
            )

            ram_lines = (
                stdout.read()
                .decode()
                .splitlines()
            )

            mem_parts = (
                ram_lines[1]
                .split()
            )

            total_ram = float(
                mem_parts[1]
            )

            used_ram = float(
                mem_parts[2]
            )

            ram_pct = round(
                (used_ram / total_ram)
                * 100,
                2,
            )

            # Disk

            stdin, stdout, stderr = client.exec_command(
                "df -h /"
            )

            disk_lines = (
                stdout.read()
                .decode()
                .splitlines()
            )

            disk_pct = int(
                disk_lines[1]
                .split()[4]
                .replace("%", "")
            )

            print(
                f"[SSH] {hostname} | "
                f"cpu={cpu_pct}% | "
                f"ram={ram_pct}% | "
                f"disk={disk_pct}%",
                flush=True,
            )

            return {
                "healthy": True,
                "response_ms": 0,
                "error_count": 0,
                "cpu_pct": cpu_pct,
                "ram_pct": ram_pct,
                "memory_mb": used_ram,
            }

        except Exception as e:

            print(
                f"[SSH] Error: {e}",
                flush=True,
            )

            return {
                "healthy": False,
                "response_ms": 9999,
                "error_count": 1,
                "cpu_pct": 0,
                "ram_pct": 0,
                "memory_mb": 0,
            }

        finally:

            client.close()