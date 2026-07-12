"""Translate raw hai session events into compact, render-ready FeedEvents."""

from __future__ import annotations

from typing import Any, Optional

from .db import utcnow
from .models import FeedEvent

# Desktop tool verbs -> human labels (M0 finding: tool_result args carry an
# `element` description authored by the model itself — use it).
_VERB = {
    "click_desktop": "Clicking",
    "double_click_desktop": "Double-clicking",
    "right_click_desktop": "Right-clicking",
    "write_desktop": "Typing",
    "press_key_desktop": "Pressing",
    "hotkey_desktop": "Pressing",
    "scroll_desktop": "Scrolling",
    "screenshot_desktop": "Looking at the screen",
    "wait": "Waiting",
}


def _label(tool: str, args: dict[str, Any]) -> str:
    verb = _VERB.get(tool, tool.replace("_desktop", "").replace("_", " ").capitalize())
    element = args.get("element")
    text = args.get("text")
    keys = args.get("keys") or args.get("key")
    if tool == "write_desktop" and text:
        return f'Typing "{str(text)[:80]}"'
    if keys:
        keys = "+".join(keys) if isinstance(keys, list) else keys
        return f"Pressing {keys}"
    if element:
        return f"{verb} {str(element)[:100]}"
    return verb


def to_feed_event(task_id: str, seq: int, raw: Any) -> Optional[FeedEvent]:
    """Map one raw session event to a FeedEvent, or None if not renderable."""
    z = getattr(raw, "event", raw)
    data = getattr(z, "data", None)
    kind = getattr(data, "kind", None)
    event_ts = getattr(z, "timestamp", None)
    ts = event_ts.isoformat() if event_ts else utcnow()

    if kind == "policy_event":
        text = (getattr(data, "reasoning_content", None) or "").strip()
        if text:
            return FeedEvent(task_id=task_id, seq=seq, kind="thinking", text=text, ts=ts)
        return None

    if kind == "tool_result":
        req = getattr(data, "tool_req", None)
        tool = getattr(req, "tool_name", "") if req else ""
        args = dict(getattr(req, "args", {}) or {}) if req else {}
        return FeedEvent(
            task_id=task_id, seq=seq, kind="action",
            text=_label(tool, args), tool=tool, args=args, ts=ts,
        )

    if kind == "observation_event":
        img = getattr(data, "image", None)
        url = getattr(img, "source", None) if img else None
        if url:
            return FeedEvent(task_id=task_id, seq=seq, kind="screenshot", image_url=url, ts=ts)
        return None

    if kind == "answer_event":
        return FeedEvent(
            task_id=task_id, seq=seq, kind="answer",
            text=str(getattr(data, "answer", "")), ts=ts,
        )

    # MetricsUpdateEvent lives on the outer event type, not data.kind
    name = type(z).__name__
    if "MetricsUpdate" in name:
        metrics = getattr(data, "metrics", None)
        if metrics is not None:
            return FeedEvent(
                task_id=task_id, seq=seq, kind="metrics",
                step=getattr(metrics, "steps", None),
                cost_usd=getattr(metrics, "total_cost", None),
                ts=ts,
            )
    return None
