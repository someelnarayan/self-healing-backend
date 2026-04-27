"""
bookshop/main.py  ·  Target Application (the site being monitored)
Intentional failure endpoints for testing the healer.

Endpoints:
  GET /            → homepage
  GET /health      → returns 200 {"status": "ok"}
  GET /crash       → kills the process (simulate a crash)
  GET /slow        → sleeps 10 s (simulate slow response)
  GET /memory-leak → allocates RAM until OOM (simulate memory leak)
  GET /orders      → fake order list
"""
import logging
import os
import sys
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI

# ── Logging to file (healer reads this) ───────────────────────────────────────
LOG_DIR = Path("/var/log/bookshop")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("bookshop")

app = FastAPI(title="Bookshop", version="1.0.0")

# In-memory "leak" bucket
_leak_bucket = []


@app.get("/")
def home():
    logger.info("Home page accessed")
    return {"shop": "The Healer Bookshop", "status": "open"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/orders")
def orders():
    logger.info("Orders fetched")
    return {"orders": [
        {"id": 1, "title": "Clean Code", "qty": 2},
        {"id": 2, "title": "The Pragmatic Programmer", "qty": 1},
    ]}


@app.get("/crash")
def crash():
    logger.error("CRASH endpoint triggered — forcing process exit")
    os._exit(1)   # Hard kill — simulates a crash


@app.get("/slow")
def slow():
    logger.warning("Slow endpoint triggered — sleeping 10 s")
    time.sleep(10)
    return {"status": "finally done"}


@app.get("/memory-leak")
def memory_leak():
    global _leak_bucket
    chunk = " " * (10 * 1024 * 1024)   # 10 MB
    _leak_bucket.append(chunk)
    logger.error(f"OOM risk — allocated chunk, total={len(_leak_bucket) * 10} MB")
    return {"allocated_mb": len(_leak_bucket) * 10}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)