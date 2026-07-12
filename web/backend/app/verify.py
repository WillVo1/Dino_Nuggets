""""Agent stopped" != "done": task-specific DB verification on the trytond server.

Runs read-only SQL over `gcloud compute ssh` (Postgres is VPC-firewalled).
Each preset maps to a check returning (passed, human_summary).
"""

from __future__ import annotations

import asyncio
from typing import Optional

from .config import settings


async def _psql(sql: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "gcloud", "compute", "ssh", settings.trytond_vm, f"--zone={settings.gcp_zone}",
        f'--command=sudo -u postgres psql -d tryton -tA -c "{sql}"',
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    return out.decode().strip()


_CHECKS = {
    "create_sale": (
        "SELECT s.number || '|' || s.state FROM sale_sale s JOIN party_party p ON s.party=p.id "
        "WHERE p.name='Pam Beesly' AND s.state='quotation' ORDER BY s.id DESC LIMIT 1",
        "quotation for Pam Beesly",
    ),
    "create_customer": (
        "SELECT cm.value FROM party_contact_mechanism cm JOIN party_party p ON cm.party=p.id "
        "WHERE p.name='Stamford Paper Co' AND cm.value='orders@stamfordpaper.com' LIMIT 1",
        "party 'Stamford Paper Co' with intact email",
    ),
    "create_product": (
        "SELECT t.name FROM product_template t WHERE t.name='Desk Lamp' AND t.salable LIMIT 1",
        "salable product 'Desk Lamp'",
    ),
    "attach_document": (
        "SELECT a.name FROM ir_attachment a WHERE a.name='acme_contract.txt' "
        "ORDER BY a.id DESC LIMIT 1",
        "attachment 'acme_contract.txt'",
    ),
}


async def verify(preset: Optional[str]) -> tuple[Optional[bool], str]:
    """(passed, summary). passed=None means no check defined for this task."""
    if not preset or preset not in _CHECKS:
        return None, "no verification defined (free-text task)"
    sql, what = _CHECKS[preset]
    try:
        out = await _psql(sql)
    except Exception as exc:
        return False, f"verification errored: {exc}"
    if out:
        return True, f"DB check passed: found {what} ({out.splitlines()[-1]})"
    return False, f"DB check failed: {what} not found"
