from __future__ import annotations

import asyncio
import json
import queue
import threading
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Response
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

app = FastAPI(title="Self-Healer", version="1.0.0")


def _control_loop():
    print("[Main] Control loop started")

    while True:
        for target in config.targets:
            try:
                print(f"[Monitor] Checking {target.name}")

                monitor.poll_once(target)

                events = analyzer.analyze(target.name)

                for ev in events:
                    print(f"[Analyzer] Event detected: {ev}")

                    if kb.is_on_cooldown(target.name):
                        print(f"[Cooldown] Skipping {target.name}")
                        continue

                    plan = planner.plan(ev)

                    if plan:
                        print(f"[Planner] Action: {plan.action_type}")

                        executor.execute(plan)

                        kb.set_cooldown(target.name, 30)

                    try:
                        _event_queue.put_nowait({
                            "type": "anomaly",
                            "data": ev.to_dict(),
                        })
                    except queue.Full:
                        pass

            except Exception as e:
                print(f"[ERROR] {target.name}: {e}")

        time.sleep(min(t.poll_interval_seconds for t in config.targets))


@app.on_event("startup")
def startup():
    t = threading.Thread(target=_control_loop, daemon=True)
    t.start()


@app.get("/health")
def healer_health():
    return {"status": "ok"}


@app.get("/status")
def status():
    return {"summary": kb.summary()}


@app.get("/stream")
async def stream():
    async def event_gen():
        while True:
            try:
                event = _event_queue.get_nowait()
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"
                await asyncio.sleep(1)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return "<h1>Self-Healer Running</h1>"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)