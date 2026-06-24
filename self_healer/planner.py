"""
planner.py · Plan (P in MAPE-K)

Responsibilities:
- Convert anomalies into recovery plans
- Select actions from config.yaml rules
- Respect cooldowns
- Support dry-run mode

Planner decides WHAT to do.
Executor decides HOW to do it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from analyzer import AnomalyEvent
from config import AppConfig, Rule, Target
from knowledge import KnowledgeBase


@dataclass
class ActionPlan:
    anomaly: AnomalyEvent
    actions: List[str]
    dry_run: bool = False
    skip_reason: Optional[str] = None

    cooldown_minutes: int = 0
    rule_name: str = ""
    metadata: dict = field(default_factory=dict)


class Planner:
    def __init__(
        self,
        config: AppConfig,
        kb: KnowledgeBase,
        dry_run: bool = False,
    ):
        self.config = config
        self.kb = kb
        self.dry_run = dry_run

    def _resolve_rule(
        self,
        anomaly: AnomalyEvent,
    ) -> Optional[Rule]:
        return self.config.rule_for(anomaly.anomaly_type)

    def _cooldown_key(
        self,
        anomaly: AnomalyEvent,
    ) -> str:
        """
        Per-target-per-anomaly cooldown.
        Example:
            ssh-test:PROCESS_DOWN
            ssh-test:HIGH_CPU
            bookshop:HEALTH_CHECK_FAIL
        """
        return f"{anomaly.target_name}:{anomaly.anomaly_type}"

    def _get_target(
        self,
        anomaly: AnomalyEvent,
    ) -> Optional[Target]:
        return self.config.get_target(anomaly.target_name)

    def _filter_actions_for_target(
        self,
        target: Optional[Target],
        anomaly: AnomalyEvent,
        actions: List[str],
    ) -> List[str]:
        """
        Remove actions that do not make sense for the current target.

        Main goals:
        - cleanup_demo should run ONLY on ssh demo target
        - restart_process should run only where a process restart command exists
        - restart_service should not run on ssh-test unless explicitly supported
        - retry_http_endpoint only makes sense if health_url exists
        """
        if not target:
            return actions

        filtered: List[str] = []

        for action in actions:
            # --------------------------------------------------
            # cleanup_demo -> only valid for SSH target with command
            # --------------------------------------------------
            if action == "cleanup_demo":
                if target.is_ssh and target.cleanup_command:
                    filtered.append(action)
                else:
                    print(
                        f"[Planner] Skipping cleanup_demo for {target.name} "
                        f"(not an SSH demo target or cleanup_command missing)",
                        flush=True,
                    )
                continue

            # --------------------------------------------------
            # restart_process -> valid only if restart command exists
            # --------------------------------------------------
            if action == "restart_process":
                if target.restart_command:
                    filtered.append(action)
                else:
                    print(
                        f"[Planner] Skipping restart_process for {target.name} "
                        f"(restart_command missing)",
                        flush=True,
                    )
                continue

            # --------------------------------------------------
            # restart_service
            #
            # For your project:
            # - local/docker app targets can use restart_service
            # - ssh target should NOT use restart_service unless you later
            #   explicitly implement a separate ssh service restart flow
            # --------------------------------------------------
            if action == "restart_service":
                if target.is_ssh:
                    print(
                        f"[Planner] Skipping restart_service for {target.name} "
                        f"(SSH target should use restart_process instead)",
                        flush=True,
                    )
                else:
                    filtered.append(action)
                continue

            # --------------------------------------------------
            # retry_http_endpoint -> only if target has health_url
            # --------------------------------------------------
            if action == "retry_http_endpoint":
                if target.health_url:
                    filtered.append(action)
                else:
                    print(
                        f"[Planner] Skipping retry_http_endpoint for {target.name} "
                        f"(health_url missing)",
                        flush=True,
                    )
                continue

            # send_alert and anything else
            filtered.append(action)

        return filtered

    def plan(
        self,
        anomaly: AnomalyEvent,
    ) -> Optional[ActionPlan]:

        rule = self._resolve_rule(anomaly)

        if not rule:
            print(
                f"[Planner] No rule found for {anomaly.anomaly_type}",
                flush=True,
            )
            return None

        target = self._get_target(anomaly)
        cooldown_key = self._cooldown_key(anomaly)

        # Build target-aware action list
        filtered_actions = self._filter_actions_for_target(
            target=target,
            anomaly=anomaly,
            actions=rule.actions,
        )

        if not filtered_actions:
            print(
                f"[Planner] No valid actions remain for "
                f"{anomaly.anomaly_type} on {anomaly.target_name}",
                flush=True,
            )
            return ActionPlan(
                anomaly=anomaly,
                actions=[],
                dry_run=self.dry_run,
                skip_reason="No valid actions for this target/anomaly combination",
                cooldown_minutes=rule.cooldown_minutes,
                rule_name=rule.anomaly_type,
                metadata={
                    "cooldown_key": cooldown_key,
                    "target_name": anomaly.target_name,
                    "anomaly_type": anomaly.anomaly_type,
                    "severity": anomaly.severity,
                    "cooldown_mode": False,
                    "target_filtered": True,
                },
            )

        # ------------------------------------------------------
        # Cooldown handling
        # ------------------------------------------------------
        if self.kb.is_on_cooldown(cooldown_key):
            remaining = self.kb.get_cooldown_remaining(cooldown_key)

            print(
                f"[Planner] Cooldown active for {cooldown_key} "
                f"({remaining}s remaining)",
                flush=True,
            )

            # During cooldown: alert only if available, else skip
            cooldown_actions = (
                ["send_alert"]
                if "send_alert" in filtered_actions
                else []
            )

            if not cooldown_actions:
                print(
                    f"[Planner] No alert action available during cooldown "
                    f"for {cooldown_key}; returning no-op plan",
                    flush=True,
                )

            return ActionPlan(
                anomaly=anomaly,
                actions=cooldown_actions,
                dry_run=self.dry_run,
                skip_reason=(
                    f"Cooldown active for {cooldown_key} "
                    f"({remaining}s remaining)"
                ),
                cooldown_minutes=rule.cooldown_minutes,
                rule_name=rule.anomaly_type,
                metadata={
                    "cooldown_key": cooldown_key,
                    "cooldown_remaining_seconds": remaining,
                    "cooldown_mode": True,
                    "target_name": anomaly.target_name,
                    "anomaly_type": anomaly.anomaly_type,
                    "severity": anomaly.severity,
                    "filtered_actions": filtered_actions,
                },
            )

        # ------------------------------------------------------
        # Normal action plan
        # ------------------------------------------------------
        print(
            f"[Planner] Selected actions {filtered_actions} "
            f"for anomaly {anomaly.anomaly_type} "
            f"on target {anomaly.target_name}",
            flush=True,
        )

        return ActionPlan(
            anomaly=anomaly,
            actions=filtered_actions,
            dry_run=self.dry_run,
            cooldown_minutes=rule.cooldown_minutes,
            rule_name=rule.anomaly_type,
            metadata={
                "cooldown_key": cooldown_key,
                "target_name": anomaly.target_name,
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
                "cooldown_mode": False,
                "filtered_actions": filtered_actions,
            },
        )