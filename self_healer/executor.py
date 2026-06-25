"""
executor.py · Execute (E in MAPE-K)

Responsibilities:
- Execute planned recovery actions
- Record audit logs
- Return action results to orchestrator / planner layer

Supported actions:
- restart_service
- restart_process
- cleanup_demo                  (backward compatibility)
- cleanup_cpu_stress           (NEW)
- cleanup_mem_stress           (NEW)
- cleanup_temp_files           (NEW)
- send_alert
- retry_http_endpoint
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Dict, Optional

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

        # Docker client reused for local/docker restart_service
        try:
            self._docker = docker.from_env()
        except Exception:
            self._docker = None

        self._action_registry: Dict[str, Callable[[Target], ActionResult]] = {
            "restart_service": self._restart_service,
            "restart_process": self._restart_process,
            "cleanup_demo": self._cleanup_demo,                   # backward compatibility
            "cleanup_cpu_stress": self._cleanup_cpu_stress,       # NEW
            "cleanup_mem_stress": self._cleanup_mem_stress,       # NEW
            "cleanup_temp_files": self._cleanup_temp_files,       # NEW
            "send_alert": self._send_alert,
            "retry_http_endpoint": self._retry_http_endpoint,
        }

    # --------------------------------------------------------------
    # Public entry point
    # --------------------------------------------------------------
    def run_action(self, action: str, target: Target) -> ActionResult:
        print(f"[Executor] Running {action} on {target.name}", flush=True)

        handler = self._action_registry.get(action)
        if not handler:
            result = ActionResult(
                action=action,
                target_name=target.name,
                success=False,
                message=f"Unknown action: {action}",
                duration_ms=0,
            )
            self._write_audit(result)
            return result

        started = time.perf_counter()
        try:
            result = handler(target)
        except Exception as e:
            duration_ms = int((time.perf_counter() - started) * 1000)
            result = ActionResult(
                action=action,
                target_name=target.name,
                success=False,
                message=f"{type(e).__name__}: {e}",
                duration_ms=duration_ms,
            )

        # If handler didn’t set duration, fill it
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
    def _restart_service(self, target: Target) -> ActionResult:
        """
        Restart a target service.

        Current behavior:
        - For docker-backed local targets (bookshop), restart container
        - For SSH demo target, falls back to restart_command if provided
        """
        if target.container_name:
            if self._docker is None:
                return ActionResult(
                    action="restart_service",
                    target_name=target.name,
                    success=False,
                    message="Docker client unavailable",
                )

            print(f"[Executor] Restarting container {target.container_name}", flush=True)
            container = self._docker.containers.get(target.container_name)
            container.restart()

            return ActionResult(
                action="restart_service",
                target_name=target.name,
                success=True,
                message=f"Restarted container {target.container_name}",
            )

        # Fallback: if SSH target or any target provides restart_command
        if target.restart_command:
            return self._run_shell_action(
                action="restart_service",
                target=target,
                command=target.restart_command,
            )

        return ActionResult(
            action="restart_service",
            target_name=target.name,
            success=False,
            message="No container_name or restart_command configured",
        )

    def _restart_process(self, target: Target) -> ActionResult:
        """
        Restart a process on SSH / demo target using restart_command.
        """
        if not target.restart_command:
            return ActionResult(
                action="restart_process",
                target_name=target.name,
                success=False,
                message="restart_command not configured",
            )

        return self._run_shell_action(
            action="restart_process",
            target=target,
            command=target.restart_command,
        )

    def _cleanup_demo(self, target: Target) -> ActionResult:
        """
        Backward-compatible generic cleanup.
        """
        if not target.cleanup_command:
            return ActionResult(
                action="cleanup_demo",
                target_name=target.name,
                success=False,
                message="cleanup_command not configured",
            )

        return self._run_shell_action(
            action="cleanup_demo",
            target=target,
            command=target.cleanup_command,
        )

    def _cleanup_cpu_stress(self, target: Target) -> ActionResult:
        """
        CPU-specific cleanup action.
        Expects cleanup_cpu_command in config.
        """
        if not target.cleanup_cpu_command:
            return ActionResult(
                action="cleanup_cpu_stress",
                target_name=target.name,
                success=False,
                message="cleanup_cpu_command not configured",
            )

        return self._run_shell_action(
            action="cleanup_cpu_stress",
            target=target,
            command=target.cleanup_cpu_command,
        )

    def _cleanup_mem_stress(self, target: Target) -> ActionResult:
        """
        Memory-specific cleanup action.
        Expects cleanup_mem_command in config.
        """
        if not target.cleanup_mem_command:
            return ActionResult(
                action="cleanup_mem_stress",
                target_name=target.name,
                success=False,
                message="cleanup_mem_command not configured",
            )

        return self._run_shell_action(
            action="cleanup_mem_stress",
            target=target,
            command=target.cleanup_mem_command,
        )

    def _cleanup_temp_files(self, target: Target) -> ActionResult:
        """
        Disk/temp-file cleanup action.
        Expects cleanup_disk_command in config.
        """
        if not target.cleanup_disk_command:
            return ActionResult(
                action="cleanup_temp_files",
                target_name=target.name,
                success=False,
                message="cleanup_disk_command not configured",
            )

        return self._run_shell_action(
            action="cleanup_temp_files",
            target=target,
            command=target.cleanup_disk_command,
        )

    def _send_alert(self, target: Target) -> ActionResult:
        """
        Placeholder alert action.
        You can later wire this into Slack / email.
        """
        message = f"Anomaly detected on target {target.name}"
        print(f"[ALERT] {message}", flush=True)

        return ActionResult(
            action="send_alert",
            target_name=target.name,
            success=True,
            message=message,
        )

    def _retry_http_endpoint(self, target: Target) -> ActionResult:
        """
        Simple retry probe for HTTP-based services.
        Useful as a soft recovery / verification action.
        """
        if not target.health_url:
            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                success=False,
                message="health_url not configured",
            )

        try:
            response = httpx.get(target.health_url, timeout=5.0)
            ok = response.status_code == 200

            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                success=ok,
                message=f"HTTP {response.status_code} from {target.health_url}",
            )

        except Exception as e:
            return ActionResult(
                action="retry_http_endpoint",
                target_name=target.name,
                success=False,
                message=f"Retry failed: {e}",
            )

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------
    def _run_shell_action(
        self,
        action: str,
        target: Target,
        command: str,
    ) -> ActionResult:
        """
        Run a shell command locally inside healer container / runtime.

        This is used for the SSH demo-lab shell scripts mounted / accessible
        to the healer runtime.
        """
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
                success=success,
                message=" | ".join(msg_parts),
            )

        except subprocess.TimeoutExpired:
            return ActionResult(
                action=action,
                target_name=target.name,
                success=False,
                message=f"Command timed out: {command}",
            )

        except Exception as e:
            return ActionResult(
                action=action,
                target_name=target.name,
                success=False,
                message=f"Shell action failed: {e}",
            )

    def _write_audit(self, result: ActionResult) -> None:
        """
        Persist action result into KnowledgeBase audit log.

        Assumes kb has write_audit(...) or equivalent.
        If your KB method name differs, adjust only this function.
        """
        try:
            # Preferred signature
            self.kb.write_audit(
                target_name=result.target_name,
                action=result.action,
                success=result.success,
                message=result.message,
            )
        except TypeError:
            # Backward-compatible fallback if KB expects slightly different args
            try:
                self.kb.write_audit(
                    result.target_name,
                    result.action,
                    result.success,
                    result.message,
                )
            except Exception as e:
                print(f"[Executor] Audit write failed: {e}", flush=True)
        except Exception as e:
            print(f"[Executor] Audit write failed: {e}", flush=True)