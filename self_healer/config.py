from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from models import TargetType


@dataclass
class Target:
    id: str
    name: str

    # local | ssh | prometheus | docker
    type: str = TargetType.LOCAL.value

    # Common monitoring / verification
    health_url: str = ""
    poll_interval_seconds: int = 10

    # Local / Docker target
    log_path: str = ""
    container_name: str = ""

    # SSH target
    host: str = ""
    username: str = ""
    ssh_key: str = ""

    # Prometheus source
    prometheus_url: str = ""

    # Future extensibility
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Thresholds:
    cpu_percent: float = 85.0
    ram_percent: float = 80.0
    response_time_ms: int = 3000
    error_rate_per_window: int = 5
    sliding_window_size: int = 5


@dataclass
class Rule:
    anomaly_type: str
    actions: List[str]
    cooldown_minutes: int = 5
    enabled: bool = True


@dataclass
class Alerting:
    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    alert_email_to: str = ""


@dataclass
class AppConfig:
    targets: List[Target]
    thresholds: Thresholds
    rules: List[Rule]
    alerting: Alerting
    knowledge_db_path: str = "knowledge.db"

    def rule_for(self, anomaly_type: str) -> Optional[Rule]:
        for rule in self.rules:
            if rule.enabled and rule.anomaly_type == anomaly_type:
                return rule
        return None


_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path = _CONFIG_PATH) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    # -------- Targets --------
    targets: List[Target] = []
    for t in raw.get("targets", []):
        target_data = dict(t)

        # Backward compatibility: if id is missing, use name
        if "id" not in target_data:
            target_data["id"] = target_data.get("name", "unknown-target")

        # Backward compatibility: metadata optional
        if "metadata" not in target_data:
            target_data["metadata"] = {}

        targets.append(Target(**target_data))

    # -------- Thresholds --------
    thresholds = Thresholds(**raw.get("thresholds", {}))

    # -------- Rules --------
    rules: List[Rule] = []
    for r in raw.get("rules", []):
        rule_data = dict(r)

        # Backward compatibility: enabled optional
        if "enabled" not in rule_data:
            rule_data["enabled"] = True

        rules.append(Rule(**rule_data))

    # -------- Alerting --------
    al = raw.get("alerting", {})

    alerting = Alerting(
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL")
        or al.get("slack_webhook_url", ""),
        smtp_host=os.getenv("SMTP_HOST")
        or al.get("smtp_host", ""),
        smtp_port=int(al.get("smtp_port", 587)),
        smtp_user=os.getenv("SMTP_USER")
        or al.get("smtp_user", ""),
        smtp_pass=os.getenv("SMTP_PASS")
        or al.get("smtp_pass", ""),
        alert_email_to=al.get("alert_email_to", ""),
    )

    return AppConfig(
        targets=targets,
        thresholds=thresholds,
        rules=rules,
        alerting=alerting,
        knowledge_db_path=raw.get("knowledge_db_path", "knowledge.db"),
    )