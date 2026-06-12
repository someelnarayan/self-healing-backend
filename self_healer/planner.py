"""
planner.py · Plan (P in MAPE-K)

Takes an AnomalyEvent and decides WHAT to do about it.

Responsibilities:
- Look up matching rule from config.yaml
- Check cooldown timers
- Build ActionPlan
- Escalate if all actions are blocked
- Support dry-run mode

Does NOT execute actions.
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

    def plan(self, anomaly: AnomalyEvent) -> Optional[ActionPlan]:

        rule = self.config.rule_for(anomaly.anomaly_type)

        if not rule:
            print(
                f"[Planner] No rule for anomaly type: "
                f"{anomaly.anomaly_type}"
            )
            return None

        available_actions = []
        blocked_actions = []

        for action in rule.actions:

            if self.kb.is_on_cooldown(anomaly.target_name):
                blocked_actions.append(action)
            else:
                available_actions.append(action)

        if not available_actions:

            print(
                f"[Planner] All actions on cooldown for "
                f"{anomaly.target_name}/{anomaly.anomaly_type}"
            )

            return ActionPlan(
                anomaly=anomaly,
                actions=["send_alert"],
                dry_run=self.dry_run,
                skip_reason=(
                    f"All actions on cooldown: "
                    f"{blocked_actions}"
                ),
            )

        return ActionPlan(
            anomaly=anomaly,
            actions=available_actions,
            dry_run=self.dry_run,
        )