#!/bin/bash
set -e

# Demo entrypoint: starts ALL apps on one desktop + hai bridge.
# Used for the end-to-end demo flow (email -> Tryton -> LibreOffice -> Slack).

export DISPLAY=:${DISPLAY_NUM:-99}
export XDG_SESSION_TYPE=x11
export HOME=/home/agent

HAI_API_KEY="${HAI_API_KEY:?HAI_API_KEY is required}"
HAI_API_BASE_URL="${HAI_API_BASE_URL:-https://agp.hcompany.ai}"
TRYTON_SERVER="${TRYTON_SERVER:-localhost:8000}"
SLACK_TOKEN="${SLACK_TOKEN:-}"
SESSION_ID="${SESSION_ID:-}"

mkdir -p /opt/agent /home/agent/.config/tryton

# ── 1. Xvfb ──────────────────────────────────────────────────────────
echo "[demo] starting Xvfb on :${DISPLAY_NUM:-99}"
Xvfb :${DISPLAY_NUM:-99} -screen 0 1920x1080x24 -nolisten tcp &
sleep 1

# ── 2. Window manager ───────────────────────────────────────────────
echo "[demo] starting openbox"
openbox &
sleep 0.5

# ── 3. Tryton client (pre-configured profile) ───────────────────────
echo "[demo] starting Tryton (server: $TRYTON_SERVER)"
cp /opt/agent/tryton-profile.conf /home/agent/.config/tryton/tryton.conf
tryton &
sleep 5

# ── 4. LibreOffice Writer (Tip of Day disabled in image) ─────────────
echo "[demo] starting LibreOffice Writer"
libreoffice --writer --norestore &
sleep 5

# ── 5. Thunderbird (skip account setup) ─────────────────────────────
echo "[demo] starting Thunderbird"
thunderbird &
sleep 8

# ── 6. Tryton auto-login (via pyautogui) ────────────────────────────
if [ -n "$TRYTON_SERVER" ]; then
    echo "[demo] auto-logging into Tryton"
    DISPLAY=:${DISPLAY_NUM:-99} /opt/agent/venv/bin/python3 /opt/agent/tryton_login.py "$TRYTON_SERVER" 2>/dev/null || true
    sleep 2
fi

# ── 7. Slack (Chromium with pre-auth token) ──────────────────────────
if [ -n "$SLACK_TOKEN" ]; then
    echo "[demo] setting up Slack auth in Chromium"
    DISPLAY=:${DISPLAY_NUM:-99} /opt/agent/venv/bin/python3 /opt/agent/slack_auth.py "$SLACK_TOKEN" 2>/dev/null || true
    DISPLAY=:${DISPLAY_NUM:-99} chromium --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-crash-reporter --no-first-run https://app.slack.com &
else
    echo "[demo] no SLACK_TOKEN, starting Chromium with Slack login page"
    DISPLAY=:${DISPLAY_NUM:-99} chromium --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-crash-reporter --no-first-run https://app.slack.com &
fi
sleep 10

# ── 8. Pre-load demo email into Thunderbird ─────────────────────────
if [ -f /opt/agent/demo_email.eml ]; then
    echo "[demo] importing demo email into Thunderbird"
    cp /opt/agent/demo_email.eml /tmp/demo_invoice.eml
fi

# ── 9. hai bridge ───────────────────────────────────────────────────
echo "[demo] starting hai local desktop bridge"
if [ -z "$SESSION_ID" ]; then
    SESSION_ID=$(/usr/bin/python3 -c "import uuid; print(uuid.uuid4())")
fi

echo "$SESSION_ID" > /opt/agent/session_id
echo "[demo] session_id=$SESSION_ID"

exec /opt/agent/venv/bin/hai local desktop --session-id "$SESSION_ID"
