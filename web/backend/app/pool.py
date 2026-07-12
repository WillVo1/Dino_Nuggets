"""Worker pool: the VMs are an invisible pool behind POST /task.

Workers are declared in workers.json; each VM's boot automation writes its
bridge session id to /opt/agent/session_id, which we read over `gcloud ssh`
on refresh. Dispatch = pick an idle worker, else FIFO-queue the task.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Optional

from .config import settings
from .models import Worker, WorkerStatus

logger = logging.getLogger(__name__)


async def _gcloud_read_session_id(vm: str) -> Optional[str]:
    proc = await asyncio.create_subprocess_exec(
        "gcloud", "compute", "ssh", vm, f"--zone={settings.gcp_zone}",
        "--command=cat /opt/agent/session_id 2>/dev/null",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    sid = out.decode().strip().splitlines()[-1].strip() if out.strip() else ""
    return sid or None


class WorkerPool:
    def __init__(self) -> None:
        self._workers: dict[str, Worker] = {}
        self._waiters: asyncio.Queue[str] = asyncio.Queue()  # task ids awaiting a worker
        self._lock = asyncio.Lock()
        self.on_free: Optional[Callable[[], None]] = None  # dispatcher hook

    def load(self) -> None:
        data = json.loads(settings.workers_file.read_text())
        for w in data["workers"]:
            self._workers[w["name"]] = Worker(name=w["name"], ip=w["ip"])
        logger.info("loaded %d workers", len(self._workers))

    async def refresh(self) -> list[Worker]:
        """Re-read each VM's bridge session id; offline -> idle when one appears."""
        async def one(w: Worker) -> None:
            sid = await _gcloud_read_session_id(w.name)
            w.session_id = sid
            if sid and w.status == WorkerStatus.OFFLINE:
                w.status = WorkerStatus.IDLE
            if not sid and w.status != WorkerStatus.BUSY:
                w.status = WorkerStatus.OFFLINE

        await asyncio.gather(*(one(w) for w in self._workers.values()))
        return self.workers

    @property
    def workers(self) -> list[Worker]:
        return list(self._workers.values())

    async def acquire(self, task_id: str) -> Optional[Worker]:
        """Return an idle worker (marking it busy), or None if all are busy/offline."""
        async with self._lock:
            for w in self._workers.values():
                if w.status == WorkerStatus.IDLE and w.session_id:
                    w.status = WorkerStatus.BUSY
                    w.current_task_id = task_id
                    return w
        return None

    async def release(self, worker_name: str) -> None:
        async with self._lock:
            w = self._workers.get(worker_name)
            if w:
                w.status = WorkerStatus.IDLE if w.session_id else WorkerStatus.OFFLINE
                w.current_task_id = None
        if self.on_free:
            self.on_free()


pool = WorkerPool()
