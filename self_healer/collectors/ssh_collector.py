from __future__ import annotations

import paramiko

from collectors.base_collector import BaseCollector


class SSHCollector(BaseCollector):
    """
    SSH-based collector for remote / demo targets.

    Collects:
    - CPU %
    - RAM %
    - Disk %
    - SSH service status
    - Demo process running status (e.g. dummy_service.py)

    Important behavior:
    - If the configured demo process is NOT running,
      this collector marks the target unhealthy so the
      analyzer/planner/executor can heal it.
    """

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
        stdout_text = stdout.read().decode().strip()
        stderr_text = stderr.read().decode().strip()

        if stderr_text:
            print(
                f"[SSH DEBUG] stderr for `{command}` => {stderr_text}",
                flush=True,
            )

        return stdout_text

    # ---------------------------------------------------------
    # CPU parser
    # ---------------------------------------------------------

    def _parse_cpu_pct(self, cpu_output: str) -> float:
        """
        Parse output like:
        Cpu(s):  2.0 us,  1.0 sy,  0.0 ni, 96.5 id, ...
        CPU% = 100 - idle
        """
        cpu_pct = 0.0

        try:
            for part in cpu_output.split(","):
                part = part.strip()

                if " id" in part:
                    idle = float(part.split()[0])
                    cpu_pct = round(100 - idle, 2)
                    break

        except Exception as e:
            print(
                f"[SSH] CPU parse error: {e}",
                flush=True,
            )

        return cpu_pct

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

            cpu_pct = self._parse_cpu_pct(cpu_output)

            print(
                f"[SSH DEBUG] cpu_pct={cpu_pct}",
                flush=True,
            )

            # -------------------------------------------------
            # RAM
            # -------------------------------------------------
            ram_output = self._run(client, "free -m")
            ram_lines = ram_output.splitlines()

            total_ram = 0.0
            used_ram = 0.0
            ram_pct = 0.0

            if len(ram_lines) >= 2:
                mem_parts = ram_lines[1].split()
                total_ram = float(mem_parts[1])
                used_ram = float(mem_parts[2])
                ram_pct = round(
                    (used_ram / total_ram) * 100,
                    2,
                )

            # -------------------------------------------------
            # Disk
            # -------------------------------------------------
            disk_output = self._run(client, "df -h /")
            disk_lines = disk_output.splitlines()

            disk_pct = 0
            if len(disk_lines) >= 2:
                disk_pct = int(
                    disk_lines[1].split()[4].replace("%", "")
                )

            # -------------------------------------------------
            # SSH service status
            # -------------------------------------------------
            ssh_status = self._run(
                client,
                "systemctl is-active ssh"
            ).strip()

            print(
                f"[SSH] ssh_service={ssh_status}",
                flush=True,
            )

            # -------------------------------------------------
            # Demo process status
            # -------------------------------------------------
            process_name = getattr(
                self.target,
                "process_name",
                "",
            )

            process_running = True
            process_status = "NOT_CONFIGURED"

            if process_name:
                # VERY IMPORTANT:
                # use a more specific command so we can see exactly
                # what is matched on the remote side
                process_cmd = f"pgrep -af '{process_name}'"

                process_output = self._run(
                    client,
                    process_cmd
                ).strip()

                print(
                    f"[SSH DEBUG] process_check_output="
                    f"{process_output or 'NONE'}",
                    flush=True,
                )

                process_running = bool(process_output)
                process_status = (
                    "RUNNING"
                    if process_running
                    else "STOPPED"
                )

                print(
                    f"[SSH] process={process_name} "
                    f"status={process_status}",
                    flush=True,
                )

            # -------------------------------------------------
            # Decide health
            # -------------------------------------------------
            healthy = True
            response_ms = 0
            error_count = 0

            # If SSH service itself is not active, mark unhealthy
            if ssh_status != "active":
                healthy = False
                response_ms = 9999
                error_count = 1

            # If demo process is configured but not running,
            # mark unhealthy so analyzer can trigger healing
            if process_name and not process_running:
                healthy = False
                response_ms = 9999
                error_count = max(error_count, 1)

            # -------------------------------------------------
            # Final Log
            # -------------------------------------------------
            print(
                f"[SSH] {hostname} | "
                f"cpu={cpu_pct}% | "
                f"ram={ram_pct}% | "
                f"disk={disk_pct}% | "
                f"ssh={ssh_status} | "
                f"process_running={process_running} | "
                f"healthy={healthy}",
                flush=True,
            )

            return {
                "healthy": healthy,
                "response_ms": response_ms,
                "error_count": error_count,
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
                "cpu_pct": 0.0,
                "ram_pct": 0.0,
                "memory_mb": 0.0,
                "ssh_status": "unknown",
                "disk_pct": 0,
                "process_running": False,
            }

        finally:
            client.close()