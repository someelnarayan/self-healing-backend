"""
main.py  ·  Orchestrator + REST API
────────────────────────────────────
Architecture:
  • FastAPI runs in the MAIN thread via Uvicorn
  • MAPE-K control loop runs in a BACKGROUND thread
  • A thread-safe queue.Queue passes anomaly events to the SSE endpoint

Endpoints:
  GET  /            → web dashboard (HTML)
  GET  /health      → healer's own health
  GET  /status      → live system status per target
  GET  /anomalies   → last 50 anomaly events
  GET  /actions     → last 50 audit log entries
  GET  /stream      → Server-Sent Events (live push to browser)
  POST /config/reload → hot-reload config.yaml without restart
"""
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
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from analyzer import Analyzer
from config import AppConfig, load_config
from executor import Executor
from knowledge import KnowledgeBase
from monitor import Monitor
from planner import Planner


# ── Global state ───────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.yaml"
config: AppConfig = load_config(CONFIG_PATH)
kb = KnowledgeBase(config.knowledge_db_path)
monitor = Monitor(config, kb)
analyzer = Analyzer(config, kb, monitor)
planner = Planner(config, kb, dry_run=False)
executor = Executor(config, kb)

# SSE event queue — monitor loop pushes, SSE endpoint consumes
_event_queue: queue.Queue = queue.Queue(maxsize=200)

app = FastAPI(title="Self-Healer", version="1.0.0")


# ── MAPE-K Control loop ────────────────────────────────────────────────────────

def _control_loop():
    """Runs in background thread: Monitor → Analyze → Plan → Execute."""
    print("[Main] Control loop started")
    while True:
        for target in config.targets:
            try:
                # M
                monitor.poll_once(target)
                # A
                events = analyzer.analyze(target.name)
                for ev in events:
                    # P
                    plan = planner.plan(ev)
                    if plan:
                        # E
                        executor.execute(plan)
                    # Push to SSE queue (non-blocking)
                    try:
                        _event_queue.put_nowait({
                            "type": "anomaly",
                            "data": ev.to_dict(),
                        })
                    except queue.Full:
                        pass
            except Exception as e:
                print(f"[Main] Control loop error on {target.name}: {e}")
        time.sleep(min(t.poll_interval_seconds for t in config.targets))


# ── Config hot-reload ──────────────────────────────────────────────────────────

class _ConfigWatcher(FileSystemEventHandler):
    def on_modified(self, event):
        if Path(event.src_path).name == "config.yaml":
            global config, monitor, analyzer, planner, executor
            try:
                config = load_config(CONFIG_PATH)
                monitor.config = config
                analyzer.config = config
                planner.config = config
                executor.config = config
                print("[Main] config.yaml reloaded")
            except Exception as e:
                print(f"[Main] Config reload failed: {e}")


# ── Startup ────────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup():
    # Start control loop thread
    t = threading.Thread(target=_control_loop, daemon=True)
    t.start()

    # Start config file watcher
    observer = Observer()
    observer.schedule(_ConfigWatcher(), str(CONFIG_PATH.parent), recursive=False)
    observer.daemon = True
    observer.start()


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/health")
def healer_health():
    return {"status": "ok", "service": "self-healer"}


@app.get("/status")
def status():
    results = []
    for target in config.targets:
        state = monitor.get_ring(target.name)
        recent = state.last_n(1)
        last = recent[-1] if recent else None
        results.append({
            "target": target.name,
            "health_ok": last.health_ok if last else None,
            "cpu_pct": last.cpu_pct if last else None,
            "ram_pct": last.ram_pct if last else None,
            "response_ms": last.response_ms if last else None,
        })
    return {"targets": results, "summary": kb.summary()}


@app.get("/anomalies")
def anomalies():
    return {"anomalies": kb.recent_anomalies(50)}


@app.get("/actions")
def actions():
    return {"actions": kb.recent_actions(50)}


@app.post("/config/reload")
def reload_config():
    try:
        global config
        config = load_config(CONFIG_PATH)
        return {"status": "reloaded"}
    except Exception as e:
        return Response(content=str(e), status_code=500)


# ── Server-Sent Events ─────────────────────────────────────────────────────────

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


# ── Dashboard ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    html_path = Path(__file__).parent / "dashboard.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Dashboard file not found</h1>"


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)