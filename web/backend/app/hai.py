"""Thin wrapper around the hai-agents SDK.

Design constraints learned in M0-M2 (see DESIGN.md §11 "M0/M1 findings"):
- No pre-registered desktop agent exists: every session passes an inline Agent
  whose Desktop environment carries the target VM's bridge session_id (the SDK
  leaves envs with an explicit session_id alone — no local bridge is spawned).
- The API can transiently 404 a fresh session (CDN consistency) — poll through it.
- Sessions created at the concurrent-trajectory cap sit `queued` and dequeue on
  their own; treat `queued` as a live state, not an error.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from hai_agents import Agent, AsyncClient, Environment_Desktop

from .config import settings

logger = logging.getLogger(__name__)

SETTLED = {"completed", "failed", "timed_out", "interrupted", "cancelled"}


def make_client() -> AsyncClient:
    return AsyncClient(api_key=settings.hai_api_key, base_url=settings.hai_base_url)


def desktop_agent(bridge_session_id: str) -> Agent:
    return Agent(
        name="local-desktop",
        description="Drives a fleet VM's Linux desktop through a user_device bridge.",
        environments=[
            Environment_Desktop(id="desk", host="user_device", session_id=bridge_session_id)
        ],
    )


async def create_task_session(client: AsyncClient, bridge_session_id: str, prompt: str) -> str:
    """Create a session targeting one VM's bridge; returns the hai session id."""
    session = await client.sessions.create_session(
        agent=desktop_agent(bridge_session_id),
        messages=prompt,
        max_steps=settings.max_steps,
    )
    return session.id


async def stream_changes(
    client: AsyncClient, session_id: str
) -> AsyncIterator[tuple[str, Optional[str], list[Any]]]:
    """Yield (status, outcome, new_events) until the session settles.

    Long-polls get_session_changes(from_index=...); rides through transient
    404s/network errors rather than failing the task.
    """
    import asyncio

    index = 0
    while True:
        try:
            changes = await client.sessions.get_session_changes(
                session_id,
                from_index=index,
                include_events=True,
                wait_for_seconds=settings.changes_wait_seconds,
            )
        except Exception as exc:  # 404-tolerant polling (M1 finding)
            logger.warning("get_session_changes retry for %s: %s", session_id, str(exc)[:120])
            await asyncio.sleep(settings.watcher_retry_seconds)
            continue

        if changes is None:
            continue

        events = list(changes.new_events or [])
        index += len(events)
        status = str(changes.status or "")
        outcome = getattr(changes, "outcome", None)
        yield status, outcome, events

        if status in SETTLED:
            return


async def cancel(client: AsyncClient, session_id: str) -> None:
    await client.sessions.cancel_session(session_id)
