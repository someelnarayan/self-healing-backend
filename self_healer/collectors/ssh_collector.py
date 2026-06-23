from collectors.base_collector import BaseCollector
import paramiko


class SSHCollector(BaseCollector):

    def __init__(self, target):
        self.target = target

    # ---------------------------------------------------------
    # SSH connection
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Small helper to run a command and return stripped stdout
    # ---------------------------------------------------------

    def _run(self, client, command: str) -> str:
        stdin, stdout, stderr = client.exec_command(command)
        return stdout.read().decode().strip()

    # ---------------------------------------------------------
    # Main collection
    # ---------------------------------------------------------

    def collect(self):
        client = self._connect()

        try:
            # -------------------------------------------------
            # Hostname
            # -------------------------------------------------
            hostname = self._run(client, "hostname")

            # -------------------------------------------------
            # CPU
            # -------------------------------------------------
            cpu_output = self._run(
                client,
                "top -bn1 | grep 'Cpu(s)'"
            )

            print(
                f"[SSH DEBUG] CPU RAW = {cpu_output}",
                flush=True,
            )

            cpu_pct = 0.0

            try:
                for part in cpu_output.split(","):
                    part = part.strip()

                    if " id" in part:
                        idle = float(part.split()[0])

                        print(
                            f"[SSH DEBUG] idle={idle}",
                            flush=True,
                        )

                        cpu_pct = round(100 - idle, 2)

                        print(
                            f"[SSH DEBUG] cpu_pct={cpu_pct}",
                            flush=True,
                        )

                        break

            except Exception as e:
                print(
                    f"[SSH] CPU parse error: {e}",
                    flush=True,
                )

            # -------------------------------------------------
            # RAM
            # -------------------------------------------------
            ram_output = self._run(client, "free -m")
            ram_lines = ram_output.splitlines()

            mem_parts = ram_lines[1].split()
            total_ram = float(mem_parts[1])
            used_ram = float(mem_parts[2])

            ram_pct = round((used_ram / total_ram) * 100, 2)

            # -------------------------------------------------
            # Disk
            # -------------------------------------------------
            disk_output = self._run(client, "df -h /")
            disk_lines = disk_output.splitlines()

            disk_pct = int(
                disk_lines[1].split()[4].replace("%", "")
            )

            # -------------------------------------------------
            # SSH service status
            # -------------------------------------------------
            ssh_status = self._run(
                client,
                "systemctl is-active ssh"
            )

            print(
                f"[SSH] ssh_service={ssh_status}",
                flush=True,
            )

            # -------------------------------------------------
            # Demo process status (NEW)
            # -------------------------------------------------
            process_running = True
            process_name = self.target.process_name

            if process_name:
                process_cmd = (
                    f"pgrep -f '{process_name}' >/dev/null && "
                    f"echo RUNNING || echo STOPPED"
                )

                process_status = self._run(
                    client,
                    process_cmd
                )

                process_running = (
                    process_status.strip() == "RUNNING"
                )

                print(
                    f"[SSH] process={process_name} "
                    f"status={process_status}",
                    flush=True,
                )

            # -------------------------------------------------
            # Final Log
            # -------------------------------------------------
            print(
                f"[SSH] {hostname} | "
                f"cpu={cpu_pct}% | "
                f"ram={ram_pct}% | "
                f"disk={disk_pct}% | "
                f"ssh={ssh_status} | "
                f"process_running={process_running}",
                flush=True,
            )

            return {
                "healthy": True,
                "response_ms": 0,
                "error_count": 0,
                "cpu_pct": cpu_pct,
                "ram_pct": ram_pct,
                "memory_mb": used_ram,
                "ssh_status": ssh_status,
                "disk_pct": disk_pct,
                "process_running": process_running,
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
                "ssh_status": "unknown",
                "disk_pct": 0,
                "process_running": False,
            }

        finally:
            client.close()