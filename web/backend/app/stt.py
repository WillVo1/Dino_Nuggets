"""Speech-to-text via Gradium's REST endpoint.

The browser records mic audio and POSTs it here; we forward the raw bytes to
Gradium (POST /api/post/speech/asr) with the server-held GRADIUM_KEY — the key
never reaches the client, same pattern as the screenshot proxy in main.py.

Gradium replies with an NDJSON stream: one JSON object per line, each carrying a
`type`. We concatenate the `text` fields of `type == "text"` lines into the full
transcript. Pre-stream failures come back as a non-200 with a plain-text body;
post-stream failures arrive as a `type == "error"` line.
"""

from __future__ import annotations

import json
import logging

import httpx

from .config import settings

logger = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when Gradium rejects the audio or streams back an error line."""


async def transcribe(audio: bytes, content_type: str, language: str = "en") -> str:
    """Send audio bytes to Gradium and return the assembled transcript text."""
    if not settings.gradium_key:
        raise TranscriptionError("GRADIUM_KEY is not set on the server")

    headers = {
        "x-api-key": settings.gradium_key,
        "Content-Type": content_type or "audio/wav",
    }
    params = {"json_config": json.dumps({"language": language})}

    segments: list[str] = []
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST", settings.gradium_stt_url, params=params, headers=headers, content=audio
        ) as resp:
            if resp.status_code != 200:
                body = (await resp.aread()).decode(errors="replace")[:300]
                raise TranscriptionError(f"gradium {resp.status_code}: {body}")
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("skipping non-JSON STT line: %s", line[:120])
                    continue
                if msg.get("type") == "text" and msg.get("text"):
                    segments.append(msg["text"])
                elif msg.get("type") == "error":
                    raise TranscriptionError(msg.get("message", "unknown STT error"))

    return " ".join(s.strip() for s in segments if s.strip()).strip()
