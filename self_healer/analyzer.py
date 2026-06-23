"""
analyzer.py · Analyze (A in MAPE-K)

Responsibilities:
- Read recent signals from Monitor
- Detect anomalies using threshold rules
- Generate AnomalyEvent objects
- Persist anomalies into KnowledgeBase

Analyzer NEVER executes actions.
Analyzer NEVER restarts services.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import List

from config import AppConfig
from knowledge import KnowledgeBase
from monitor import Monitor, Signal


# ------------------------------------------------------------------
# Anomaly Event
# ------------------------------------------------------------------

@dataclass
class AnomalyEvent:
    anomaly_type: str
    severity: str
    target_name: str
    metric_value: float
    context: dict
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)


# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def _all_above(
    signals: List[Signal],
    attr: str,
    threshold: float,
) -> bool:
    if not signals:
        return False

    return all(
        getattr(signal, attr, 0) > threshold
        for signal in signals
    )


def _memory_leak_trend(
    signals: List[Signal],
    min_growth: float = 15.0,
) -> bool:
    """
    Detects a likely memory leak pattern:
    - need at least 5 signals
    - RAM keeps increasing across the window
    - total RAM growth exceeds min_growth
    """
    if len(signals) < 5:
        return False

    values = [signal.ram_pct for signal in signals]

    increasing_steps = sum(
        1
        for i in range(1, len(values))
        if values[i] > values[i - 1]
    )

    growth = values[-1] - values[0]

    return (
        increasing_steps >= len(values) - 1
        and growth >= min_growth
    )


# ------------------------------------------------------------------
# Analyzer
# ------------------------------------------------------------------

class Analyzer:
    def __init__(
        self,
        config: AppConfig,
        kb: KnowledgeBase,
        monitor: Monitor,
    ):
        self.config = config
        self.kb = kb
        self.monitor = monitor

    def analyze(
        self,
        target_name: str,
    ) -> List[AnomalyEvent]:

        thresholds = self.config.thresholds
        window_size = thresholds.sliding_window_size

        state = self.monitor.get_ring(target_name)
        window = state.last_n(window_size)

        if len(window) < window_size:
            print(
                f"[Analyzer] Waiting for more signals "
                f"({len(window)}/{window_size})",
                flush=True,
            )
            return []

        events: List[AnomalyEvent] = []
        latest = window[-1]

        # Resolve the actual Target object so analyzer can make
        # target-aware decisions (SSH vs local vs prometheus)
        target = self.config.get_target(target_name)

        # ----------------------------------------------------------
        # SSH PROCESS DOWN (NEW)
        # If the monitored SSH demo process is not running,
        # create PROCESS_DOWN anomaly immediately.
        # ----------------------------------------------------------
        if (
            target is not None
            and target.is_ssh
            and target.process_name
            and not latest.process_running
        ):
            events.append(
                AnomalyEvent(
                    anomaly_type="PROCESS_DOWN",
                    severity="CRITICAL",
                    target_name=target_name,
                    metric_value=0.0,
                    context={
                        "process_name": target.process_name,
                        "process_running": latest.process_running,
                        "host": target.host,
                    },
                )
            )

        # ----------------------------------------------------------
        # HEALTH CHECK FAILURE
        # Require consecutive failures
        # ----------------------------------------------------------
        consecutive_failures = 0

        for signal in reversed(window):
            if not signal.health_ok:
                consecutive_failures += 1
            else:
                break

        if consecutive_failures >= 2:
            events.append(
                AnomalyEvent(
                    anomaly_type="HEALTH_CHECK_FAIL",
                    severity=(
                        "CRITICAL"
                        if consecutive_failures >= window_size
                        else "HIGH"
                    ),
                    target_name=target_name,
                    metric_value=float(consecutive_failures),
                    context={
                        "consecutive_failures": consecutive_failures,
                        "window_size": window_size,
                    },
                )
            )

        # ----------------------------------------------------------
        # HIGH CPU
        # Trigger only if CPU stays above threshold for whole window
        # ----------------------------------------------------------
        if _all_above(
            window,
            "cpu_pct",
            thresholds.cpu_percent,
        ):
            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_CPU",
                    severity="HIGH",
                    target_name=target_name,
                    metric_value=latest.cpu_pct,
                    context={
                        "cpu_pct": latest.cpu_pct,
                        "threshold": thresholds.cpu_percent,
                    },
                )
            )

        # ----------------------------------------------------------
        # HIGH RAM
        # Trigger if RAM stays above threshold for whole window
        # ----------------------------------------------------------
        if _all_above(
            window,
            "ram_pct",
            thresholds.ram_percent,
        ):
            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_RAM",
                    severity="HIGH",
                    target_name=target_name,
                    metric_value=latest.ram_pct,
                    context={
                        "ram_pct": latest.ram_pct,
                        "threshold": thresholds.ram_percent,
                    },
                )
            )

        # ----------------------------------------------------------
        # MEMORY LEAK TREND
        # Detect steady RAM growth across the window
        # ----------------------------------------------------------
        if _memory_leak_trend(window):
            events.append(
                AnomalyEvent(
                    anomaly_type="MEMORY_LEAK",
                    severity="HIGH",
                    target_name=target_name,
                    metric_value=latest.ram_pct,
                    context={
                        "start_ram": window[0].ram_pct,
                        "end_ram": latest.ram_pct,
                        "growth": latest.ram_pct - window[0].ram_pct,
                    },
                )
            )

        # ----------------------------------------------------------
        # SLOW RESPONSE
        # ----------------------------------------------------------
        if _all_above(
            window,
            "response_ms",
            thresholds.response_time_ms,
        ):
            events.append(
                AnomalyEvent(
                    anomaly_type="SLOW_RESPONSE",
                    severity="MEDIUM",
                    target_name=target_name,
                    metric_value=latest.response_ms,
                    context={
                        "response_ms": latest.response_ms,
                        "threshold": thresholds.response_time_ms,
                    },
                )
            )

        # ----------------------------------------------------------
        # HIGH ERROR RATE
        # ----------------------------------------------------------
        total_errors = sum(
            signal.error_count
            for signal in window
        )

        if total_errors >= thresholds.error_rate_per_window:
            events.append(
                AnomalyEvent(
                    anomaly_type="HIGH_ERROR_RATE",
                    severity="HIGH",
                    target_name=target_name,
                    metric_value=float(total_errors),
                    context={
                        "total_errors": total_errors,
                        "threshold": thresholds.error_rate_per_window,
                    },
                )
            )

        # ----------------------------------------------------------
        # Deduplicate by anomaly type
        # ----------------------------------------------------------
        unique_events: List[AnomalyEvent] = []
        seen = set()

        for event in events:
            if event.anomaly_type not in seen:
                seen.add(event.anomaly_type)
                unique_events.append(event)

        # ----------------------------------------------------------
        # Persist anomalies
        # ----------------------------------------------------------
        for event in unique_events:
            if self.kb.incident_exists(
                event.target_name,
                event.anomaly_type,
            ):
                continue

            self.kb.create_incident(
                event.target_name,
                event.anomaly_type,
            )

            print(
                f"[Analyzer] Detected {event.anomaly_type} "
                f"on {event.target_name}",
                flush=True,
            )

            self.kb.write_anomaly(
                target_name=event.target_name,
                anomaly_type=event.anomaly_type,
                severity=event.severity,
                metric_value=event.metric_value,
                context=json.dumps(event.context),
            )

        return unique_events