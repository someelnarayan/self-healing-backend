"""
executor.py  ·  Execute (E in MAPE-K)
Plugin-style action registry — each action is a standalone function.
Executor iterates the ActionPlan, runs each action, verifies recovery,
writes every result to the audit_log, and sets cooldown timers.

Adding a new action = add one function + register it in ACTION_REGISTRY.
No other file needs to change. (Plugin architecture)
"""
from __future__ import annotations

import smtplib
import time
from email.mime.text import MIMEText
from typing import Dict, Optional

import httpx

from config import AppConfig
from knowledge import KnowledgeBase
from planner import ActionPlan


# ── Result wrapper ─────────────────────────────────────────────────────────────

class ActionResult:
    def __init__(self, success: bool, duration_ms: int,
                 error: Optional[str] = None):
        self.success = success
        self.duration_ms = duration_ms
        self.error = error


# ── Individual action implementations ─────────────────────────────────────────

def restart_service(target_name: str, config: AppConfig) -> ActionResult:
    """Restart the Docker container, then verify /health comes back."""
    start = time.time()
    target = next((t for t in config.targets if t.name == target_name), None)
    if not target:
        return ActionResult(False, 0, f"Unknown target: {target_name}")
    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(target.container_name)
        container.restart()

        # Poll health for up to 30 s
        for _ in range(30):
            time.sleep(1)
            try:
                resp = httpx.get(target.health_url, timeout=3)
                if resp.status_code == 200:
                    ms = int((time.time() - start) * 1000)
                    return ActionResult(True, ms)
            except Exception:
                pass
        return ActionResult(False, int((time.time() - start) * 1000),
                            "Health check did not recover within 30 s")
    except Exception as e:
        return ActionResult(False, int((time.time() - start) * 1000), str(e))


def retry_http_endpoint(target_name: str, config: AppConfig) -> ActionResult:
    """Retry the /health endpoint up to 3 times with exponential backoff."""
    start = time.time()
    target = next((t for t in config.targets if t.name == target_name), None)
    if not target:
        return ActionResult(False, 0, f"Unknown target: {target_name}")
    delay = 1
    for attempt in range(3):
        try:
            resp = httpx.get(target.health_url, timeout=5)
            if resp.status_code == 200:
                return ActionResult(True, int((time.time() - start) * 1000))
        except Exception:
            pass
        time.sleep(delay)
        delay *= 2
    return ActionResult(False, int((time.time() - start) * 1000),
                        "Endpoint did not respond after 3 retries")


def send_alert(target_name: str, config: AppConfig,
               message: str = "") -> ActionResult:
    """Send alert to Slack webhook and/or email."""
    start = time.time()
    sent = False

    # Slack
    if config.alerting.slack_webhook_url:
        try:
            payload = {"text": f"🚨 *Self-Healer Alert* [{target_name}]\n{message}"}
            httpx.post(config.alerting.slack_webhook_url,
                       json=payload, timeout=5)
            sent = True
        except Exception as e:
            print(f"[Executor] Slack alert failed: {e}")

    # Email
    if config.alerting.smtp_host and config.alerting.alert_email_to:
        try:
            msg = MIMEText(
                f"Self-Healer Alert\nTarget: {target_name}\n\n{message}")
            msg["Subject"] = f"[Healer] Alert: {target_name}"
            msg["From"] = config.alerting.smtp_user
            msg["To"] = config.alerting.alert_email_to
            with smtplib.SMTP(config.alerting.smtp_host,
                               config.alerting.smtp_port) as server:
                server.starttls()
                server.login(config.alerting.smtp_user,
                              config.alerting.smtp_pass)
                server.send_message(msg)
            sent = True
        except Exception as e:
            print(f"[Executor] Email alert failed: {e}")

    if not sent:
        # Fallback: just print — alert never blocks other actions
        print(f"[ALERT] {target_name}: {message}")

    return ActionResult(True, int((time.time() - start) * 1000))


def rotate_log(target_name: str, config: AppConfig) -> ActionResult:
    """Rename current log to .bak and create a fresh file."""
    import os
    start = time.time()
    target = next((t for t in config.targets if t.name == target_name), None)
    if not target:
        return ActionResult(False, 0, f"Unknown target: {target_name}")
    try:
        bak = target.log_path + f".bak.{int(time.time())}"
        os.rename(target.log_path, bak)
        open(target.log_path, "w").close()
        return ActionResult(True, int((time.time() - start) * 1000))
    except Exception as e:
        return ActionResult(False, int((time.time() - start) * 1000), str(e))


# ── Action registry (Plugin architecture) ─────────────────────────────────────
# To add a new action:  def my_action(target_name, config) -> ActionResult
# Then add it here. Nothing else changes.

ACTION_REGISTRY: Dict = {
    "restart_service":      restart_service,
    "retry_http_endpoint":  retry_http_endpoint,
    "send_alert":           send_alert,
    "rotate_log":           rotate_log,
}


# ── Executor ───────────────────────────────────────────────────────────────────

class Executor:
    def __init__(self, config: AppConfig, kb: KnowledgeBase):
        self.config = config
        self.kb = kb

    def execute(self, plan: ActionPlan) -> list[ActionResult]:
        results = []
        anomaly = plan.anomaly
        alert_msg = (
            f"Anomaly: {anomaly.anomaly_type} | "
            f"Severity: {anomaly.severity} | "
            f"Value: {anomaly.metric_value} | "
            f"Context: {anomaly.context}"
        )

        for action_name in plan.actions:
            fn = ACTION_REGISTRY.get(action_name)
            if not fn:
                print(f"[Executor] Unknown action: {action_name}")
                continue

            if plan.dry_run:
                print(f"[DRY RUN] Would execute: {action_name} "
                      f"on {anomaly.target_name}")
                self.kb.write_audit(
                    anomaly.target_name, anomaly.anomaly_type,
                    action_name, True, 0, dry_run=True
                )
                continue

            print(f"[Executor] Running: {action_name} on {anomaly.target_name}")
            try:
                if action_name == "send_alert":
                    result = fn(anomaly.target_name, self.config, alert_msg)
                else:
                    result = fn(anomaly.target_name, self.config)
            except Exception as e:
                result = ActionResult(False, 0, str(e))

            self.kb.write_audit(
                anomaly.target_name, anomaly.anomaly_type,
                action_name, result.success, result.duration_ms,
                result.error
            )
            if result.success:
                self.kb.set_cooldown(anomaly.target_name, action_name)

            results.append(result)
            print(f"[Executor] {action_name} → "
                  f"{'✓' if result.success else '✗'} "
                  f"({result.duration_ms} ms)")

        return results
    