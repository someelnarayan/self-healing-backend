from __future__ import annotations

import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict

import docker
import httpx

from config import AppConfig, Target
from knowledge import KnowledgeBase


# ------------------------------------------------------------------
# Action Result
# ------------------------------------------------------------------

@dataclass
class ActionResult:
    action: str
    target_name: str
    anomaly_type: str
    success: bool
    message: str = ""
    duration_ms: int = 0


# ------------------------------------------------------------------
# Executor
# ------------------------------------------------------------------

class Executor:
    def __init__(self, config: AppConfig, kb: KnowledgeBase):
        self.config = config
        self.kb = kb

        try:
            self._docker = docker.from_env()
        except Exception:
            self._docker = None

        self._action_registry: Dict[str, Callable[[Target, str], ActionResult]] = {
            "restart_service": self._restart_service,
            "restart_process": self._restart_process,
            "cleanup_demo": self._cleanup_demo,
            "cleanup_cpu_stress": self._cleanup_cpu_stress,
            "cleanup_mem_stress": self._cleanup_mem_stress,
            "cleanup_temp_files": self._cleanup_temp_files,
            "send_alert": self._send_alert,
            "retry_http_endpoint": self._retry_http_endpoint,
        }

    # --------------------------------------------------------------
    # Public entry point
    # --------------------------------------------------------------
    def run_action(
        self,
        action: str,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        print(f"[Executor] Running {action} on {target.name}", flush=True)

        handler = self._action_registry.get(action)
        if not handler:
            result = ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"Unknown action: {action}",
                duration_ms=0,
            )
            self._write_audit(result)
            return result

        started = time.perf_counter()

        try:
            result = handler(target, anomaly_type)
        except Exception as e:
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"{type(e).__name__}: {e}",
                duration_ms=duration_ms,
            )

        if result.duration_ms == 0:
            result.duration_ms = int((time.perf_counter() - started) * 1000)

        self._write_audit(result)

        status = "SUCCESS" if result.success else "FAILED"
        print(
            f"[Executor] {action} -> {status} ({result.duration_ms} ms)",
            flush=True,
        )
        if result.message:
            print(f"[Executor] {action} detail: {result.message}", flush=True)

        return result

    # --------------------------------------------------------------
    # Action handlers
    # --------------------------------------------------------------
    def _restart_service(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        # Local Docker service restart (bookshop)
        if target.container_name:
            if self._docker is None:
                return ActionResult(
                    action="restart_service",
                    target_name=target.name,
                    anomaly_type=anomaly_type,
                    success=False,
                    message="Docker client unavailable",
                )

            print(
                f"[Executor] Restarting container {target.container_name}",
                flush=True,
            )
            container = self._docker.containers.get(target.container_name)
            container.restart()

            return ActionResult(
                action="restart_service",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=True,
                message=f"Restarted container {target.container_name}",
            )

        # SSH / shell fallback
        if target.restart_command:
            return self._run_target_command(
                action="restart_service",
                target=target,
                anomaly_type=anomaly_type,
                command=target.restart_command,
            )

        return ActionResult(
            action="restart_service",
            target_name=target.name,
            anomaly_type=anomaly_type,
            success=False,
            message="No container_name or restart_command configured",
        )

    def _restart_process(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        if not target.restart_command:
            return ActionResult(
                action="restart_process",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="restart_command not configured",
            )

        return self._run_target_command(
            action="restart_process",
            target=target,
            anomaly_type=anomaly_type,
            command=target.restart_command,
        )

    def _cleanup_demo(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        if not target.cleanup_command:
            return ActionResult(
                action="cleanup_demo",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="cleanup_command not configured",
            )

        return self._run_target_command(
            action="cleanup_demo",
            target=target,
            anomaly_type=anomaly_type,
            command=target.cleanup_command,
        )

    def _cleanup_cpu_stress(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        cleanup_cmd = getattr(target, "cleanup_cpu_command", "")
        if not cleanup_cmd:
            return ActionResult(
                action="cleanup_cpu_stress",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="cleanup_cpu_command not configured",
            )

        return self._run_target_command(
            action="cleanup_cpu_stress",
            target=target,
            anomaly_type=anomaly_type,
            command=cleanup_cmd,
        )

    def _cleanup_mem_stress(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        cleanup_cmd = getattr(target, "cleanup_mem_command", "")
        if not cleanup_cmd:
            return ActionResult(
                action="cleanup_mem_stress",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="cleanup_mem_command not configured",
            )

        return self._run_target_command(
            action="cleanup_mem_stress",
            target=target,
            anomaly_type=anomaly_type,
            command=cleanup_cmd,
        )

    def _cleanup_temp_files(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        cleanup_cmd = getattr(target, "cleanup_disk_command", "")
        if not cleanup_cmd:
            return ActionResult(
                action="cleanup_temp_files",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="cleanup_disk_command not configured",
            )

        return self._run_target_command(
            action="cleanup_temp_files",
            target=target,
            anomaly_type=anomaly_type,
            command=cleanup_cmd,
        )

    def _send_alert(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        message = f"Anomaly detected on target {target.name}"
        print(f"[ALERT] {message}", flush=True)

        return ActionResult(
            action="send_alert",
            target_name=target.name,
            anomaly_type=anomaly_type,
            success=True,
            message=message,
        )

    def _retry_http_endpoint(
        self,
        target: Target,
        anomaly_type: str,
    ) -> ActionResult:
        if not target.health_url:
            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="health_url not configured",
            )

        try:
            response = httpx.get(target.health_url, timeout=5.0)
            ok = response.status_code == 200

            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=ok,
                message=f"HTTP {response.status_code} from {target.health_url}",
            )

        except Exception as e:
            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"Retry failed: {e}",
            )

    # --------------------------------------------------------------
    # Target command execution
    # --------------------------------------------------------------
    def _run_target_command(
        self,
        action: str,
        target: Target,
        anomaly_type: str,
        command: str,
    ) -> ActionResult:
        """
        Execute a command:
        - locally for local targets
        - via SSH for ssh targets
        """
        if target.is_ssh:
            return self._run_ssh_command(
                action=action,
                target=target,
                anomaly_type=anomaly_type,
                remote_command=command,
            )

        return self._run_local_shell_action(
            action=action,
            target=target,
            anomaly_type=anomaly_type,
            command=command,
        )

    def _run_local_shell_action(
        self,
        action: str,
        target: Target,
        anomaly_type: str,
        command: str,
    ) -> ActionResult:
        try:
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=60,
            )

            success = completed.returncode == 0
            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()

            msg_parts = []
            if stdout:
                msg_parts.append(f"stdout={stdout}")
            if stderr:
                msg_parts.append(f"stderr={stderr}")
            if not msg_parts:
                msg_parts.append(f"returncode={completed.returncode}")

            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=success,
                message=" | ".join(msg_parts),
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"Command timed out: {command}",
            )

        except Exception as e:
            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"Shell action failed: {e}",
            )

    def _run_ssh_command(
        self,
        action: str,
        target: Target,
        anomaly_type: str,
        remote_command: str,
    ) -> ActionResult:
        """
        Execute command on SSH target host.
        """
        if not target.host or not target.username or not target.ssh_key:
            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message="SSH target missing host/username/ssh_key",
            )

        ssh_cmd = [
            "ssh",
            "-i",
            target.ssh_key,
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            f"{target.username}@{target.host}",
            remote_command,
        ]

        try:
            completed = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=90,
            )

            success = completed.returncode == 0
            stdout = (completed.stdout or "").strip()
            stderr = (completed.stderr or "").strip()

            msg_parts = [f"ssh_command={remote_command}"]
            if stdout:
                msg_parts.append(f"stdout={stdout}")
            if stderr:
                msg_parts.append(f"stderr={stderr}")
            if not stdout and not stderr:
                msg_parts.append(f"returncode={completed.returncode}")

            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=success,
                message=" | ".join(msg_parts),
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"SSH command timed out: {remote_command}",
            )

        except Exception as e:
            return ActionResult(
                action=action,
                target_name=target.name,
                anomaly_type=anomaly_type,
                success=False,
                message=f"SSH action failed: {e}",
            )

    # --------------------------------------------------------------
    # Audit
    # --------------------------------------------------------------
    def _write_audit(self, result: ActionResult) -> None:
        try:
            self.kb.write_audit(
                target_name=result.target_name,
                anomaly_type=result.anomaly_type,
                action=result.action,
                success=result.success,
                duration_ms=result.duration_ms,
                error_msg=None if result.success else result.message,
            )
        except Exception as e:
            print(f"[Executor] Audit write failed: {e}", flush=True)