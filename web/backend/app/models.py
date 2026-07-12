"""API and domain models."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED_LOCAL = "queued_local"    # waiting for an idle worker (our FIFO)
    QUEUED_REMOTE = "queued_remote"  # session created; H Company has it queued (slot cap)
    RUNNING = "running"
    VERIFYING = "verifying"          # agent finished; running the DB check
    SUCCEEDED = "succeeded"          # agent done + verification passed
    DONE_UNVERIFIED = "done_unverified"  # agent done; no verification defined
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (
            TaskStatus.SUCCEEDED,
            TaskStatus.DONE_UNVERIFIED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        )


class WorkerStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"  # no registered bridge session


class Worker(BaseModel):
    name: str                      # e.g. "agent-vm-1"
    ip: str
    session_id: Optional[str] = None
    status: WorkerStatus = WorkerStatus.OFFLINE
    current_task_id: Optional[str] = None


class TaskCreate(BaseModel):
    text: str = Field(min_length=1, description="Plain-language task, or a preset key")
    preset: Optional[str] = None   # one of prompts.PRESETS keys; overrides text template


class Task(BaseModel):
    id: str
    text: str                      # what the user typed
    prompt: str                    # enriched prompt actually sent
    preset: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED_LOCAL
    worker: Optional[str] = None
    hai_session_id: Optional[str] = None
    answer: Optional[str] = None
    outcome: Optional[str] = None
    verification: Optional[str] = None  # human-readable verification result
    steps: int = 0
    cost_usd: float = 0.0
    last_screenshot_url: Optional[str] = None
    created_at: str = ""
    finished_at: Optional[str] = None


class FeedEvent(BaseModel):
    """Compact, render-ready feed item derived from a hai session event."""

    task_id: str
    seq: int
    kind: str                      # thinking | action | screenshot | answer | status | metrics
    text: Optional[str] = None     # thinking text / action label / answer
    tool: Optional[str] = None     # e.g. click_desktop, write_desktop
    args: Optional[dict[str, Any]] = None
    image_url: Optional[str] = None
    step: Optional[int] = None
    cost_usd: Optional[float] = None
    ts: str = ""
