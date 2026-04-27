"""
planner.py  ·  Plan (P in MAPE-K)
Takes an AnomalyEvent and decides WHAT to do about it.

Responsibilities:
  - Look up the matching rule from config.yaml
  - Check cooldown timers before approving any action
  - Build an ordered ActionPlan (list of actions to try)
  - Escalate to CRITICAL alert if all actions are blocked by cooldown
  - Support dry_run mode (log intent, never execute)

Does NOT execute anything. Hands the plan to executor.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from analyzer import AnomalyEvent
from config import AppConfig
from knowledge import KnowledgeBase


@dataclass
class ActionPlan:
    anomaly: AnomalyEvent
    actions: List[str]          # ordered list of actions to attempt
    dry_run: bool = False
    skip_reason: Optional[str] = None   # set if all actions blocked


class Planner:
    def __init__(self, config: AppConfig, kb: KnowledgeBase,
                 dry_run: bool = False):
        self.config = config
        self.kb = kb
        self.dry_run = dry_run

    def plan(self, anomaly: AnomalyEvent) -> Optional[ActionPlan]:
        """
        Returns an ActionPlan, or None if no rule matches.
        """
        rule = self.config.rule_for(anomaly.anomaly_type)
        if not rule:
            print(f"[Planner] No rule for anomaly type: {anomaly.anomaly_type}")
            return None

        available_actions = []
        blocked_actions = []

        for action in rule.actions:
            if self.kb.is_on_cooldown(anomaly.target_name, action,
                                      rule.cooldown_minutes):
                blocked_actions.append(action)
            else:
                available_actions.append(action)

        # If everything is on cooldown, escalate
        if not available_actions:
            print(f"[Planner] All actions on cooldown for "
                  f"{anomaly.target_name}/{anomaly.anomaly_type} — escalating")
            return ActionPlan(
                anomaly=anomaly,
                actions=["send_alert"],    # always available escalation
                dry_run=self.dry_run,
                skip_reason=f"All primary actions on cooldown: {blocked_actions}",
            )

        return ActionPlan(
            anomaly=anomaly,
            actions=available_actions,
            dry_run=self.dry_run,
        )