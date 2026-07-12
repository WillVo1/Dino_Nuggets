"""Fleet control plane: FastAPI app wiring routes, WS, and lifecycle."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .config import settings
from .db import db
from .dispatcher import dispatcher
from .models import TaskCreate
from .pool import pool
from .prompts import PRESETS
from .ws import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    pool.load()
    await pool.refresh()
    dispatcher.start()
    yield
    await db.close()


app = FastAPI(title="Tryton Fleet Control Plane", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/presets")
async def presets():
    return [{"key": k, "label": v["label"]} for k, v in PRESETS.items()]


@app.get("/api/workers")
async def workers():
    return [w.model_dump() for w in pool.workers]


@app.post("/api/workers/refresh")
async def workers_refresh():
    return [w.model_dump() for w in await pool.refresh()]


@app.post("/api/task", status_code=201)
async def create_task(body: TaskCreate):
    task = await dispatcher.submit(body.text, body.preset)
    return task.model_dump()


@app.get("/api/tasks")
async def list_tasks():
    return [t.model_dump() for t in await db.list_tasks()]


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    task = await db.get_task(task_id)
    if not task:
        raise HTTPException(404)
    events = await db.list_events(task_id)
    return {"task": task.model_dump(), "events": [e.model_dump() for e in events]}


@app.post("/api/tasks/{task_id}/stop")
async def stop_task(task_id: str):
    ok = await dispatcher.stop(task_id)
    if not ok:
        raise HTTPException(409, "task not running")
    return {"stopped": True}


@app.get("/api/screenshot")
async def screenshot(url: str):
    """Proxy session screenshots: browser <img> tags can't send the bearer token."""
    host = httpx.URL(url).host
    if host not in settings.allowed_screenshot_hosts:
        raise HTTPException(400, "host not allowed")
    async with httpx.AsyncClient() as client:
        r = await client.get(
            url, headers={"Authorization": f"Bearer {settings.hai_api_key}"},
            follow_redirects=True, timeout=20,
        )
    return Response(
        content=r.content,
        media_type=r.headers.get("content-type", "image/png"),
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.websocket("/ws")
async def websocket(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # client pings; we only broadcast
    except WebSocketDisconnect:
        manager.disconnect(ws)
