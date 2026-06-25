from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from analyzer import Analyzer
from config import AppConfig, load_config
from executor import Executor
from knowledge import KnowledgeBase
from monitor import Monitor
from planner import Planner

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


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _event_put(event_type: str, data: dict):
    try:
        _event_queue.put_nowait(
            {
                "type": event_type,
                "data": data,
            }
        )
    except queue.Full:
        pass


# -------------------------------------------------------------------
# Main control loop
# -------------------------------------------------------------------

def _control_loop():
    print("[Main] Control loop started", flush=True)

    if not config.targets:
        print("[Main] No targets configured", flush=True)
        return

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

                # --------------------------------------------------
                # 1) Monitor
                # --------------------------------------------------
                monitor.poll_once(target)

                # --------------------------------------------------
                # 2) Analyze
                # --------------------------------------------------
                events = analyzer.analyze(target.name)

                if not events:
                    continue

                # --------------------------------------------------
                # 3) Plan + Execute for each anomaly
                # --------------------------------------------------
                for ev in events:
                    print(
                        f"[Analyzer] Event detected: {ev.anomaly_type} "
                        f"on {ev.target_name}",
                        flush=True,
                    )

                    _event_put(
                        "anomaly",
                        ev.to_dict(),
                    )

                    plan = planner.plan(ev)

                    if not plan:
                        print(
                            f"[Planner] No plan produced for "
                            f"{ev.anomaly_type} on {ev.target_name}",
                            flush=True,
                        )
                        continue

                    # If planner intentionally skipped, log it but do not execute
                    if plan.skip_reason and not plan.actions:
                        print(
                            f"[Planner] Skipping execution for "
                            f"{ev.anomaly_type} on {ev.target_name}: "
                            f"{plan.skip_reason}",
                            flush=True,
                        )

                        _event_put(
                            "plan_skipped",
                            {
                                "target_name": ev.target_name,
                                "anomaly_type": ev.anomaly_type,
                                "skip_reason": plan.skip_reason,
                                "actions": plan.actions,
                            },
                        )
                        continue

                    print(
                        f"[Planner] Actions for {ev.target_name} / "
                        f"{ev.anomaly_type}: {plan.actions}",
                        flush=True,
                    )

                    # --------------------------------------------------
                    # 4) Execute
                    # --------------------------------------------------
                    if plan.actions:
                        target_obj = config.get_target(ev.target_name)

                        if not target_obj:
                            print(
                                f"[Executor] Target not found for execution: {ev.target_name}",
                                flush=True,
                            )
                        else:
                            for action in plan.actions:
                                result = executor.run_action(
                                    action=action,
                                    target=target_obj,
                                    anomaly_type=ev.anomaly_type,
                                )

                                _event_put(
                                    "action_result",
                                    {
                                        "target_name": ev.target_name,
                                        "anomaly_type": ev.anomaly_type,
                                        "action": result.action,
                                        "success": result.success,
                                        "message": result.message,
                                        "duration_ms": result.duration_ms,
                                    },
                                )
                    else:
                        print(
                            f"[Executor] No executable actions for "
                            f"{ev.target_name} / {ev.anomaly_type}",
                            flush=True,
                        )

                    # --------------------------------------------------
                    # 5) Set cooldown using planner's anomaly-specific key
                    # --------------------------------------------------
                    cooldown_key = plan.metadata.get("cooldown_key", "")
                    cooldown_minutes = plan.cooldown_minutes or 0
                    cooldown_mode = plan.metadata.get("cooldown_mode", False)

                    if (
                        plan.actions
                        and cooldown_key
                        and cooldown_minutes > 0
                        and not cooldown_mode
                    ):
                        kb.set_cooldown(
                            cooldown_key,
                            cooldown_minutes * 60,
                        )

                        print(
                            f"[Cooldown] Set cooldown for "
                            f"{cooldown_key} "
                            f"({cooldown_minutes} min)",
                            flush=True,
                        )

                    _event_put(
                        "plan_executed",
                        {
                            "target_name": ev.target_name,
                            "anomaly_type": ev.anomaly_type,
                            "actions": plan.actions,
                            "cooldown_key": cooldown_key,
                            "cooldown_minutes": cooldown_minutes,
                            "cooldown_mode": cooldown_mode,
                        },
                    )

            except Exception as e:
                print(
                    f"[ERROR] {target.name}: {e}",
                    flush=True,
                )

                _event_put(
                    "loop_error",
                    {
                        "target_name": target.name,
                        "error": str(e),
                    },
                )

        time.sleep(poll_interval)


# -------------------------------------------------------------------
# Startup
# -------------------------------------------------------------------

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


# -------------------------------------------------------------------
# Basic health / targets
# -------------------------------------------------------------------

@app.get("/health")
def healer_health():
    return {
        "status": "ok",
        "service": "self-healer",
    }


@app.get("/targets")
def targets():
    return [
        {
            "id": t.id,
            "name": t.name,
            "type": t.type,
        }
        for t in config.targets
    ]


@app.get("/status")
def status():
    return {
        "summary": kb.summary(),
    }


# -------------------------------------------------------------------
# Signals / anomalies / audit
# -------------------------------------------------------------------

@app.get("/signals")
def signals(limit: int = 100, target: str | None = None):
    return kb.get_signals(limit=limit, target_name=target)


@app.get("/anomalies")
def anomalies(limit: int = 100, target: str | None = None):
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


# -------------------------------------------------------------------
# Recovery / cooldown status
# -------------------------------------------------------------------

@app.get("/recovery")
def recovery():
    rows = []

    for target in config.targets:
        for rule in config.rules:
            cooldown_key = f"{target.name}:{rule.anomaly_type}"

            rows.append(
                {
                    "target": target.name,
                    "anomaly_type": rule.anomaly_type,
                    "on_cooldown": kb.is_on_cooldown(cooldown_key),
                    "cooldown_remaining": kb.get_cooldown_remaining(cooldown_key),
                }
            )

    return rows


# -------------------------------------------------------------------
# Event stream
# -------------------------------------------------------------------

@app.get("/stream")
async def stream():
    async def event_generator():
        while True:
            try:
                event = _event_queue.get_nowait()
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


# -------------------------------------------------------------------
# Tiny HTML landing page
# -------------------------------------------------------------------

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
                <li><a href="/targets">Targets</a></li>
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