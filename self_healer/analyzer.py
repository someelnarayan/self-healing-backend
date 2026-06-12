"""
analyzer.py  ·  Analyze (A in MAPE-K)
Reads the last N signals from the ring buffer.
Applies sliding-window rules and a decision tree to classify anomalies.

Outputs: list[AnomalyEvent]  (empty list = system is healthy)

STRICT RULE: Analyzer never calls executor or planner.
It only reads from Monitor's ring buffer and writes anomalies to KnowledgeBase.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional

from config import AppConfig, Thresholds
from knowledge import KnowledgeBase
from monitor import Monitor, Signal


# ── AnomalyEvent ───────────────────────────────────────────────────────────────

@dataclass
class AnomalyEvent:
    anomaly_type: str          # MEMORY_LEAK | HIGH_CPU | HEALTH_CHECK_FAIL | etc.
    severity: str              # LOW | MEDIUM | HIGH | CRITICAL
    target_name: str
    metric_value: float
    context: dict
    ts: str = ""

    def __post_init__(self):
        if not self.ts:
            self.ts = datetime.utcnow().isoformat()

    def to_dict(self):
        return asdict(self)


# ── Sliding window helpers ─────────────────────────────────────────────────────

def _all_above(signals: List[Signal], attr: str, threshold: float) -> bool:
    """True if ALL signals in window have attr > threshold."""
    if not signals:
        return False
    return all(getattr(s, attr) > threshold for s in signals)


def _any_false(signals: List[Signal], attr: str) -> bool:
    return any(not getattr(s, attr) for s in signals)


# ── Analyzer ───────────────────────────────────────────────────────────────────

class Analyzer:
    def __init__(self, config: AppConfig, kb: KnowledgeBase, monitor: Monitor):
        self.config = config
        self.kb = kb
        self.monitor = monitor
        self._seen: dict = {}

    def analyze(self, target_name: str) -> List[AnomalyEvent]:
        """Run all checks for one target. Returns list of anomaly events."""
        thr = self.config.thresholds
        w = thr.sliding_window_size
        state = self.monitor.get_ring(target_name)
        window = state.last_n(w)

        if len(window) < w:
            return []   # not enough data yet

        events: List[AnomalyEvent] = []

        # ① Memory leak
        if _all_above(window, "ram_pct", thr.ram_percent):
            last = window[-1]
            ctx = {
                "ram_pct": last.ram_pct,
                "health_ok": last.health_ok,
                "error_count": last.error_count,
            }
            # Decision tree: high RAM + health failing → MEMORY_LEAK not traffic spike
            if not last.health_ok or last.error_count > 0:
                events.append(AnomalyEvent(
                    anomaly_type="MEMORY_LEAK",
                    severity="HIGH",
                    target_name=target_name,
                    metric_value=last.ram_pct,
                    context=ctx,
                ))
            else:
                events.append(AnomalyEvent(
                    anomaly_type="MEMORY_LEAK",
                    severity="MEDIUM",
                    target_name=target_name,
                    metric_value=last.ram_pct,
                    context=ctx,
                ))

        # ② High CPU
        if _all_above(window, "cpu_pct", thr.cpu_percent):
            last = window[-1]
            events.append(AnomalyEvent(
                anomaly_type="HIGH_CPU",
                severity="MEDIUM",
                target_name=target_name,
                metric_value=last.cpu_pct,
                context={"cpu_pct": last.cpu_pct},
            ))

        # ③ Health check failure
        if _any_false(window, "health_ok"):
            last = window[-1]
            fail_count = sum(1 for s in window if not s.health_ok)
            events.append(AnomalyEvent(
                anomaly_type="HEALTH_CHECK_FAIL",
                severity="CRITICAL" if fail_count >= w else "HIGH",
                target_name=target_name,
                metric_value=float(fail_count),
                context={"fail_count": fail_count, "window_size": w},
            ))

        # ④ Slow response time
        if _all_above(window, "response_ms", thr.response_time_ms):
            last = window[-1]
            events.append(AnomalyEvent(
                anomaly_type="SLOW_RESPONSE",
                severity="MEDIUM",
                target_name=target_name,
                metric_value=last.response_ms,
                context={"response_ms": last.response_ms,
                         "threshold_ms": thr.response_time_ms},
            ))

        # ⑤ High error rate
        total_errors = sum(s.error_count for s in window)
        if total_errors >= thr.error_rate_per_window:
            events.append(AnomalyEvent(
                anomaly_type="HIGH_ERROR_RATE",
                severity="HIGH",
                target_name=target_name,
                metric_value=float(total_errors),
                context={"total_errors_in_window": total_errors},
            ))

        # Deduplicate — don't fire same anomaly type twice in one cycle
        unique = self._deduplicate(events)

        # Persist to knowledge base
        for ev in unique:
            self.kb.write_anomaly(
                target_name=ev.target_name,
                anomaly_type=ev.anomaly_type,
                severity=ev.severity,
                metric_value=ev.metric_value,
                context=json.dumps(ev.context),
            )

        return unique

    def _deduplicate(self, events: List[AnomalyEvent]) -> List[AnomalyEvent]:
        unique = []
        seen_types = set()
        for ev in events:
            if ev.anomaly_type not in seen_types:
                seen_types.add(ev.anomaly_type)
                unique.append(ev)
        return unique