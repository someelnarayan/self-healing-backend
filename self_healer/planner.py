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

from dataclasses import dataclass
from typing import List, Optional

from analyzer import AnomalyEvent
from config import AppConfig
from knowledge import KnowledgeBase


@dataclass
class ActionPlan:
    anomaly: AnomalyEvent
    actions: List[str]
    dry_run: bool = False
    skip_reason: Optional[str] = None


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

    def plan(
        self,
        anomaly: AnomalyEvent,
    ) -> Optional[ActionPlan]:

        rule = self.config.rule_for(
            anomaly.anomaly_type
        )

        if not rule:

            print(
                f"[Planner] No rule found for "
                f"{anomaly.anomaly_type}",
                flush=True,
            )

            return None

        target_name = anomaly.target_name

        if self.kb.is_on_cooldown(target_name):

            remaining = (
                self.kb.get_cooldown_remaining(
                    target_name
                )
            )

            print(
                f"[Planner] Target "
                f"{target_name} "
                f"is on cooldown "
                f"({remaining}s remaining)",
                flush=True,
            )

            return ActionPlan(
                anomaly=anomaly,
                actions=["send_alert"],
                dry_run=self.dry_run,
                skip_reason=(
                    f"Cooldown active "
                    f"({remaining}s remaining)"
                ),
            )

        print(
            f"[Planner] Selected actions "
            f"{rule.actions} "
            f"for anomaly "
            f"{anomaly.anomaly_type}",
            flush=True,
        )

        return ActionPlan(
            anomaly=anomaly,
            actions=rule.actions,
            dry_run=self.dry_run,
        )