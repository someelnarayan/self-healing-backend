"""
tests/test_analyzer.py
Unit tests for analyzer.py — synthetic signal data, assert correct anomaly types.
Run: pytest tests/test_analyzer.py -v
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "healer"))

from self_healer.healer.analyzer import Analyzer
from self_healer.healer.config import AppConfig, Thresholds, Rule, Target, Alerting
from self_healer.healer.knowledge import KnowledgeBase
from self_healer.healer.monitor import Signal, TargetState


def _make_config():
    return AppConfig(
        targets=[Target("bookshop", "http://localhost:8080/health",
                        "/tmp/app.log", "bookshop")],
        thresholds=Thresholds(
            cpu_percent=85.0, ram_percent=80.0,
            response_time_ms=3000, error_rate_per_window=5,
            sliding_window_size=3,
        ),
        rules=[
            Rule("MEMORY_LEAK",       ["restart_service", "send_alert"], 5),
            Rule("HIGH_CPU",          ["send_alert"], 10),
            Rule("HEALTH_CHECK_FAIL", ["restart_service"], 3),
            Rule("HIGH_ERROR_RATE",   ["send_alert"], 5),
            Rule("SLOW_RESPONSE",     ["send_alert"], 10),
        ],
        alerting=Alerting(),
        knowledge_db_path=":memory:",
    )


def _signals(n, **overrides) -> list:
    base = dict(cpu_pct=10.0, ram_pct=20.0, response_ms=200,
                health_ok=True, error_count=0)
    base.update(overrides)
    return [Signal(ts=datetime.utcnow(), target_name="bookshop", **base)
            for _ in range(n)]


def _analyzer(config, signals):
    kb = KnowledgeBase(":memory:")
    monitor = MagicMock()
    state = MagicMock()
    state.last_n.return_value = signals
    monitor.get_ring.return_value = state
    return Analyzer(config, kb, monitor)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_no_anomaly_when_healthy():
    config = _make_config()
    sigs = _signals(3)
    az = _analyzer(config, sigs)
    assert az.analyze("bookshop") == []


def test_memory_leak_detected():
    config = _make_config()
    sigs = _signals(3, ram_pct=90.0, health_ok=False)
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert "MEMORY_LEAK" in types


def test_high_cpu_detected():
    config = _make_config()
    sigs = _signals(3, cpu_pct=92.0)
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert "HIGH_CPU" in types


def test_health_fail_detected():
    config = _make_config()
    sigs = _signals(3, health_ok=False)
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert "HEALTH_CHECK_FAIL" in types


def test_slow_response_detected():
    config = _make_config()
    sigs = _signals(3, response_ms=5000)
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert "SLOW_RESPONSE" in types


def test_high_error_rate_detected():
    config = _make_config()
    sigs = _signals(3, error_count=3)  # 3×3 = 9 ≥ threshold 5
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert "HIGH_ERROR_RATE" in types


def test_not_enough_data_returns_empty():
    config = _make_config()
    sigs = _signals(2, ram_pct=95.0)   # window=3, only 2 signals
    az = _analyzer(config, sigs)
    assert az.analyze("bookshop") == []


def test_deduplication():
    config = _make_config()
    sigs = _signals(3, ram_pct=95.0, cpu_pct=95.0, health_ok=False)
    az = _analyzer(config, sigs)
    events = az.analyze("bookshop")
    types = [e.anomaly_type for e in events]
    assert len(types) == len(set(types))