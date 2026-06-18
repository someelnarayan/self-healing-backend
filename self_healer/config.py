"""
config.py  ·  Config loader + validator
Reads config.yaml, exposes typed dataclasses to every other module.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml


# ── Dataclasses ────────────────────────────────────────────────────────────────

from dataclasses import dataclass


@dataclass
class Target:
    name: str

    # Target type
    # local | ssh | prometheus
    type: str = "local"

    # Local monitoring
    health_url: str = ""
    log_path: str = ""
    container_name: str = ""

    # Monitoring interval
    poll_interval_seconds: int = 10

    # SSH monitoring (Phase 2)
    host: str = ""
    username: str = ""
    ssh_key: str = ""

    # Prometheus monitoring (Phase 3)
    prometheus_url: str = ""


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
    knowledge_db_path: str = "/tmp/knowledge.db"

    def rule_for(self, anomaly_type: str) -> Optional[Rule]:
        for r in self.rules:
            if r.anomaly_type == anomaly_type:
                return r
        return None


# ── Loader ─────────────────────────────────────────────────────────────────────

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path = _CONFIG_PATH) -> AppConfig:
    with open(path) as f:
        raw = yaml.safe_load(f)

    targets = [Target(**t) for t in raw.get("targets", [])]
    thresholds = Thresholds(**raw.get("thresholds", {}))
    rules = [Rule(**r) for r in raw.get("rules", [])]

    al = raw.get("alerting", {})
    alerting = Alerting(
        slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL") or al.get("slack_webhook_url", ""),
        smtp_host=os.getenv("SMTP_HOST") or al.get("smtp_host", ""),
        smtp_port=int(al.get("smtp_port", 587)),
        smtp_user=os.getenv("SMTP_USER") or al.get("smtp_user", ""),
        smtp_pass=os.getenv("SMTP_PASS") or al.get("smtp_pass", ""),
        alert_email_to=al.get("alert_email_to", ""),
    )

    return AppConfig(
        targets=targets,
        thresholds=thresholds,
        rules=rules,
        alerting=alerting,
        knowledge_db_path=raw.get("knowledge_db_path", "/tmp/knowledge.db"),
    )