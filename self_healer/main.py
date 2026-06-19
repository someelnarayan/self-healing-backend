from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

from analyzer import Analyzer
from config import AppConfig, load_config
from executor import Executor
from knowledge import KnowledgeBase
from monitor import Monitor
from planner import Planner
from fastapi.middleware.cors import CORSMiddleware

print("MAIN FILE LOADED")


CONFIG_PATH = Path(__file__).parent / "config.yaml"

config: AppConfig = load_config(CONFIG_PATH)

kb = KnowledgeBase(config.knowledge_db_path)

monitor = Monitor(config, kb)
analyzer = Analyzer(config, kb, monitor)
planner = Planner(config, kb, dry_run=False)
executor = Executor(config, kb)

_event_queue: queue.Queue = queue.Queue(maxsize=200)

app = FastAPI(
    title="Self-Healing Backend System",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _control_loop():
    print("[Main] Control loop started", flush=True)

    poll_interval = min(
        target.poll_interval_seconds
        for target in config.targets
    )

    while True:
        for target in config.targets:
            try:
                print(
                    f"[Monitor] Checking {target.name}",
                    flush=True,
                )

                monitor.poll_once(target)

                events = analyzer.analyze(target.name)

                for ev in events:
                    print(
                        f"[Analyzer] Event detected: "
                        f"{ev.anomaly_type}",
                        flush=True,
                    )

                    if kb.is_on_cooldown(target.name):
                        print(
                            f"[Cooldown] "
                            f"{target.name} is on cooldown",
                            flush=True,
                        )
                        continue

                    plan = planner.plan(ev)

                    if plan:
                        print(
                            f"[Planner] Actions: "
                            f"{plan.actions}",
                            flush=True,
                        )

                        executor.execute(plan)

                        kb.set_cooldown(
                            target.name,
                            30,
                        )

                    try:
                        _event_queue.put_nowait(
                            {
                                "type": "anomaly",
                                "data": ev.to_dict(),
                            }
                        )
                    except queue.Full:
                        pass

            except Exception as e:
                print(
                    f"[ERROR] "
                    f"{target.name}: {e}",
                    flush=True,
                )

        time.sleep(poll_interval)


@app.on_event("startup")
def startup():
    print(
        "[Startup] Launching control loop thread",
        flush=True,
    )

    thread = threading.Thread(
        target=_control_loop,
        daemon=True,
        name="control-loop",
    )

    thread.start()


@app.get("/health")
def healer_health():
    return {
        "status": "ok",
        "service": "self-healer",
    }


@app.get("/status")
def status():
    return {
        "summary": kb.summary(),
    }


@app.get("/signals")
def signals(limit: int = 100, target: str | None = None):
    """
    Returns recent signal_log entries (newest first).
    Used by the Signals page and Live Metrics charts.
    """
    return kb.get_signals(limit=limit, target_name=target)


@app.get("/anomalies")
def anomalies(limit: int = 100, target: str | None = None):
    """
    Returns recent anomaly_log entries (newest first), reshaped to
    match the React AnomalyTable component's expected fields:
        timestamp, type, service, severity, status

    `status` is derived: an anomaly is "resolved" if at least one
    audit_log entry exists for the same target + anomaly_type with
    success = true, otherwise it is "open".
    """
    raw = kb.get_anomalies(limit=limit, target_name=target)
    audits = kb.get_audit(limit=500)

    resolved_pairs = {
        (a["target_name"], a["anomaly_type"])
        for a in audits
        if a["success"]
    }

    return [
        {
            "id": row["id"],
            "timestamp": row["ts"],
            "type": row["anomaly_type"],
            "service": row["target_name"],
            "severity": row["severity"],
            "metric_value": row["metric_value"],
            "context": row["context"],
            "status": (
                "resolved"
                if (row["target_name"], row["anomaly_type"]) in resolved_pairs
                else "open"
            ),
        }
        for row in raw
    ]


@app.get("/audit")
def audit(limit: int = 100, target: str | None = None):
    """
    Returns recent audit_log entries (newest first), reshaped to
    match the React AuditTable component's expected fields:
        timestamp, action, target, result
    """
    raw = kb.get_audit(limit=limit, target_name=target)

    return [
        {
            "id": row["id"],
            "timestamp": row["ts"],
            "action": row["action"],
            "target": row["target_name"],
            "result": "success" if row["success"] else "failed",
            "anomaly_type": row["anomaly_type"],
            "duration_ms": row["duration_ms"],
            "error_msg": row["error_msg"],
        }
        for row in raw
    ]


@app.get("/recovery")
def recovery():
    """
    Returns cooldown status for every configured target.
    Used by the Recovery page to show which services are
    currently blocked from re-triggering a recovery action.
    """
    return [
        {
            "target": t.name,
            "on_cooldown": kb.is_on_cooldown(t.name),
            "cooldown_remaining": kb.get_cooldown_remaining(t.name),
        }
        for t in config.targets
    ]

@app.get("/targets")
def targets():

    return [
        {
            "name": t.name,
            "type": t.type,
        }
        for t in config.targets
    ]




@app.get("/stream")
async def stream():

    async def event_generator():
        while True:
            try:
                event = _event_queue.get_nowait()

                yield (
                    f"data: "
                    f"{json.dumps(event)}\n\n"
                )

            except queue.Empty:
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """
    <html>
        <head>
            <title>Self-Healer Dashboard</title>
        </head>
        <body>
            <h1>Self-Healing Backend System</h1>
            <p>Service is running.</p>

            <ul>
                <li><a href="/health">Health</a></li>
                <li><a href="/status">Status</a></li>
                <li><a href="/signals">Signals</a></li>
                <li><a href="/anomalies">Anomalies</a></li>
                <li><a href="/audit">Audit</a></li>
                <li><a href="/recovery">Recovery</a></li>
                <li><a href="/stream">Event Stream</a></li>
            </ul>
        </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

