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
from config import AppConfig, Rule
from knowledge import KnowledgeBase


@dataclass
class ActionPlan:
    anomaly: AnomalyEvent
    actions: List[str]
    dry_run: bool = False
    skip_reason: Optional[str] = None

    # Added for richer planning / later playbook support
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
        Use a per-target-per-anomaly cooldown key instead of only target-level cooldown.
        This avoids one anomaly blocking every other anomaly on the same target.
        """
        return f"{anomaly.target_name}:{anomaly.anomaly_type}"

    def plan(
        self,
        anomaly: AnomalyEvent,
    ) -> Optional[ActionPlan]:

        rule = self._resolve_rule(anomaly)

        if not rule:
            print(
                f"[Planner] No rule found for "
                f"{anomaly.anomaly_type}",
                flush=True,
            )
            return None

        cooldown_key = self._cooldown_key(anomaly)

        if self.kb.is_on_cooldown(cooldown_key):
            remaining = self.kb.get_cooldown_remaining(cooldown_key)

            print(
                f"[Planner] Cooldown active for "
                f"{cooldown_key} "
                f"({remaining}s remaining)",
                flush=True,
            )

            # During cooldown, downgrade to alert-only if possible
            cooldown_actions = (
                ["send_alert"]
                if "send_alert" in rule.actions
                else []
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
                },
            )

        print(
            f"[Planner] Selected actions {rule.actions} "
            f"for anomaly {anomaly.anomaly_type} "
            f"on target {anomaly.target_name}",
            flush=True,
        )

        return ActionPlan(
            anomaly=anomaly,
            actions=rule.actions,
            dry_run=self.dry_run,
            cooldown_minutes=rule.cooldown_minutes,
            rule_name=rule.anomaly_type,
            metadata={
                "cooldown_key": cooldown_key,
                "target_name": anomaly.target_name,
                "anomaly_type": anomaly.anomaly_type,
                "severity": anomaly.severity,
            },
        )