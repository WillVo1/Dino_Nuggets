"""Application settings, sourced from environment / .env."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    """Runtime configuration. Immutable after import."""

    hai_api_key: str = os.environ.get("HAI_API_KEY", "")
    hai_base_url: str | None = os.environ.get("HAI_BASE_URL") or None  # SDK default = EU

    db_path: Path = Path(os.environ.get("FLEET_DB", BACKEND_DIR / "fleet.db"))
    workers_file: Path = Path(os.environ.get("WORKERS_FILE", BACKEND_DIR / "workers.json"))

    gcp_zone: str = os.environ.get("GCP_ZONE", "us-east4-a")
    trytond_vm: str = os.environ.get("TRYTOND_VM", "trytond-server")

    # Per-run budget (user decision 2026-07-11: max steps, default time)
    max_steps: int = int(os.environ.get("MAX_STEPS", "200"))

    # Long-poll tuning for the event watcher
    changes_wait_seconds: int = 15
    watcher_retry_seconds: float = 3.0

    allowed_screenshot_hosts = ("agp.eu.hcompany.ai", "agp.hcompany.ai")


settings = Settings()

if not settings.hai_api_key:
    raise RuntimeError("HAI_API_KEY is not set — copy .env.example to .env and fill it in")
