"""Auto-dispatch: task -> idle worker -> hai session -> watcher -> verify.

Lifecycle (statuses in models.TaskStatus):
  queued_local -> (worker acquired) -> queued_remote|running -> verifying
               -> succeeded | done_unverified | failed | cancelled
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Optional

from .db import db, utcnow
from .feed import to_feed_event
from .hai import cancel, create_task_session, make_client, stream_changes
from .models import Task, TaskStatus
from .pool import pool
from .prompts import build_prompt
from .verify import verify
from .ws import manager

logger = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()  # FIFO of task ids
        self._watchers: dict[str, asyncio.Task] = {}
        self._client = None

    def start(self) -> None:
        self._client = make_client()
        pool.on_free = lambda: None  # queue loop below polls; hook kept for future push
        asyncio.create_task(self._dispatch_loop())

    async def submit(self, text: str, preset: Optional[str]) -> Task:
        task = Task(
            id=uuid.uuid4().hex[:12],
            text=text,
            preset=preset,
            prompt=build_prompt(text, preset),
            status=TaskStatus.QUEUED_LOCAL,
            created_at=utcnow(),
        )
        await db.insert_task(task)
        await self._queue.put(task.id)
        await manager.broadcast("task", task.model_dump())
        return task

    async def stop(self, task_id: str) -> bool:
        task = await db.get_task(task_id)
        if not task or task.status.is_terminal:
            return False
        if task.hai_session_id:
            try:
                await cancel(self._client, task.hai_session_id)
            except Exception as exc:
                logger.warning("cancel failed for %s: %s", task_id, exc)
        await self._finish(task_id, TaskStatus.CANCELLED, worker=task.worker)
        return True

    # -- internals -------------------------------------------------------------

    async def _dispatch_loop(self) -> None:
        """FIFO consumer: assign each queued task to the next idle worker."""
        while True:
            task_id = await self._queue.get()
            worker = None
            while worker is None:
                worker = await pool.acquire(task_id)
                if worker is None:
                    await asyncio.sleep(2)  # all busy/offline; FIFO order preserved
            try:
                await self._launch(task_id, worker.name, worker.session_id)
            except Exception as exc:
                logger.exception("launch failed for %s", task_id)
                await pool.release(worker.name)
                await self._finish(task_id, TaskStatus.FAILED, error=str(exc))

    async def _launch(self, task_id: str, worker_name: str, bridge_sid: str) -> None:
        task = await db.get_task(task_id)
        session_id = await create_task_session(self._client, bridge_sid, task.prompt)
        await db.update_task(task_id, worker=worker_name, hai_session_id=session_id,
                             status=TaskStatus.QUEUED_REMOTE)
        await self._broadcast_task(task_id)
        self._watchers[task_id] = asyncio.create_task(
            self._watch(task_id, worker_name, session_id)
        )

    async def _watch(self, task_id: str, worker_name: str, session_id: str) -> None:
        seq = 0
        steps, cost = 0, 0.0
        final_status, outcome = "", None
        try:
            async for status, out, events in stream_changes(self._client, session_id):
                final_status, outcome = status, out
                mapped_status = (
                    TaskStatus.QUEUED_REMOTE if status == "queued" else TaskStatus.RUNNING
                )
                for raw in events:
                    fe = to_feed_event(task_id, seq, raw)
                    seq += 1
                    if fe is None:
                        continue
                    await db.append_event(fe)
                    if fe.kind == "screenshot":
                        await db.update_task(task_id, last_screenshot_url=fe.image_url)
                    if fe.kind == "metrics":
                        steps, cost = fe.step or steps, fe.cost_usd or cost
                        await db.update_task(task_id, steps=steps, cost_usd=cost)
                    if fe.kind == "answer":
                        await db.update_task(task_id, answer=fe.text)
                    await manager.broadcast("event", fe.model_dump())
                await db.update_task(task_id, status=mapped_status)
                await self._broadcast_task(task_id)
        except Exception:
            logger.exception("watcher crashed for %s", task_id)
            final_status = "failed"

        # settled: verify, then finish
        if final_status == "completed" and outcome in ("success", "partial", None):
            task = await db.get_task(task_id)
            await db.update_task(task_id, status=TaskStatus.VERIFYING, outcome=outcome)
            await self._broadcast_task(task_id)
            passed, summary = await verify(task.preset)
            status = (
                TaskStatus.SUCCEEDED if passed
                else TaskStatus.DONE_UNVERIFIED if passed is None
                else TaskStatus.FAILED
            )
            await self._finish(task_id, status, worker=worker_name,
                               verification=summary, outcome=outcome)
        else:
            await self._finish(task_id, TaskStatus.FAILED, worker=worker_name,
                               outcome=outcome or final_status)

    async def _finish(self, task_id: str, status: TaskStatus, worker: str | None = None,
                      verification: str | None = None, outcome: str | None = None,
                      error: str | None = None) -> None:
        fields = {"status": status, "finished_at": utcnow()}
        if verification:
            fields["verification"] = verification
        if outcome:
            fields["outcome"] = outcome
        if error:
            fields["verification"] = f"error: {error[:200]}"
        await db.update_task(task_id, **fields)
        if worker:
            await pool.release(worker)
        await self._broadcast_task(task_id)

    async def _broadcast_task(self, task_id: str) -> None:
        task = await db.get_task(task_id)
        if task:
            await manager.broadcast("task", task.model_dump())


dispatcher = Dispatcher()
