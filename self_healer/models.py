from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime


class TargetType(str, Enum):
    LOCAL = "local"
    SSH = "ssh"
    DOCKER = "docker"
    PROMETHEUS = "prometheus"


class AnomalyType(str, Enum):
    SERVICE_DOWN = "SERVICE_DOWN"
    HEALTH_CHECK_FAIL = "HEALTH_CHECK_FAIL"
    PROCESS_CRASH = "PROCESS_CRASH"
    HIGH_CPU = "HIGH_CPU"
    HIGH_RAM = "HIGH_RAM"
    DISK_FULL = "DISK_FULL"
    TEMP_STORAGE_BLOAT = "TEMP_STORAGE_BLOAT"
    LOG_VOLUME_EXPLOSION = "LOG_VOLUME_EXPLOSION"
    UNKNOWN = "UNKNOWN"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryActionType(str, Enum):
    RESTART_CONTAINER = "restart_container"
    START_CONTAINER = "start_container"
    RESTART_SERVICE = "restart_service"
    RESTART_PROCESS = "restart_process"
    CLEANUP_TEMP = "cleanup_temp"
    ROTATE_LOGS = "rotate_logs"
    VERIFY_HTTP_HEALTH = "verify_http_health"
    VERIFY_PROCESS = "verify_process"
    VERIFY_CONTAINER = "verify_container"
    NO_OP = "no_op"


@dataclass
class Target:
    id: str
    name: str
    type: TargetType
    host: Optional[str] = None
    port: Optional[int] = None
    health_endpoint: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signal:
    target_id: str
    source: str
    timestamp: datetime
    metrics: Dict[str, Any] = field(default_factory=dict)
    healthy: Optional[bool] = None
    message: Optional[str] = None


@dataclass
class Anomaly:
    target_id: str
    anomaly_type: AnomalyType
    severity: Severity
    reason: str
    detected_at: datetime
    signal_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    action_type: RecoveryActionType
    target_id: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionResult:
    target_id: str
    action_type: str
    success: bool
    message: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Incident:
    incident_id: str
    target_id: str
    anomaly: Anomaly
    actions: List[RecoveryAction] = field(default_factory=list)
    status: str = "OPEN"   # OPEN / RESOLVED / FAILED
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None