# Verified: `hai` runs on headless Linux via the pip SDK — no `hai-agent-runtime` binary

**Claim tested:** H Company's `hai` computer-use agent runs on Linux using only the
pip SDK's pure-Python bridge (no `hai-agent-runtime` binary), driving a headless Xvfb display.

**Verdict: TRUE, with one required one-line patch.** Reproduced end-to-end twice: a real
Holo3 *cloud* session drove a *headless Linux desktop* in Docker and wrote a sentinel file
(`HOLO_DROVE_LINUX`). No `hai-agent-runtime` was installed anywhere (`which hai-agent-runtime` → ABSENT).

Environment: Docker `python:3.13-slim`, arm64, `hai-agents[desktop]==1.0.6` +
`hai-drivers==0.1.1` (both `py3-none-any` pure-Python wheels). Cloud endpoint: US
`agp.hcompany.ai` (EU also authenticated). Key: repo `.env` `HCOMPANY_KEY`.

## Architecture confirmed (matches DESIGN.md §3)
- `holo-desktop-cli` (this repo) is a **thin client to the closed binary** — it does NOT
  contain the bridge. The bridge lives in the separate PyPI package `hai-agents[desktop]`:
  `hai_agents_local.{LocalBridge, PyautoguiDesktopBridge, BridgeManager}` +
  `hai_drivers.desktop.local.LocalDesktopDriver`.
- `Client.run_session(...)` → `LocalSessionsClient.create_session` → `_localize` →
  `ensure_bridges` auto-spawns a `PyautoguiDesktopBridge` for any `host="user_device"`
  desktop env, stamps its `session_id`, and `LocalBridge.run()` long-polls the cloud over
  `httpx` (bearer auth), executing each action via the local driver. Exactly the claimed shape.

## Blockers found + fixes (all in the Dockerfile)
1. **`evdev` build fails** (pulled by `pynput` on Linux, C extension) → install `gcc build-essential linux-libc-dev python3-dev`.
2. **`mouseinfo` import fails** (pyautogui needs tkinter on Linux) → install `python3-tk`.
3. **pyscreeze screenshots fail** ("install gnome-screenshot") → it only uses `scrot` when
   `XDG_SESSION_TYPE=x11`; set that env var (scrot already installed). No gnome-screenshot needed.
4. **Keystrokes silently don't land** (the load-bearing one) → the driver's *mouse* path uses
   pyautogui (works on Xvfb) but its *keyboard* path uses **pynput's `Controller`, whose XTEST
   events do NOT land in focused windows under Xvfb**. pyautogui's keyboard DOES land.
   Fix = `holo_linux_patch.py`: monkeypatch `LocalDesktopDriver.{write,press_key,release_key,tap_key,hotkey}`
   to route through pyautogui. Import it once before starting the bridge.
   - ⚠️ Without this patch the session still returns `status=idle` / `answer="DONE"` — the model
     **hallucinates success** — but nothing is typed. Silent failure; must patch.
   - A window manager (openbox) is also needed so the target window actually holds keyboard focus.

## Repro
```bash
docker build -t hai-linux-test linux-runtime-proof/
KEY=$(grep '^HCOMPANY_KEY=' .env | cut -d= -f2-)
docker run --rm -e HAI_API_KEY="$KEY" -e HAI_REGION=US -e PYTHONPATH=/scripts \
  -v "$PWD/linux-runtime-proof/scripts:/scripts" hai-linux-test bash -c '
    Xvfb :99 -screen 0 1280x800x24 -nolisten tcp & export DISPLAY=:99
    sleep 2; openbox & sleep 0.5; xterm & sleep 1
    WID=$(xdotool search --name xterm|head -1); xdotool windowactivate "$WID"; xdotool windowfocus "$WID"
    python -c "import holo_linux_patch; import runpy; runpy.run_path(\"/scripts/e2e_test.py\", run_name=\"__main__\")"'
# => ✅ PROOF FILE PRESENT: 'HOLO_DROVE_LINUX'
```

## What this means for DESIGN.md
The §4 constraint "Linux `hai` runtime is not shipped → Linux containers blocked" is **false in
practice**. The installer's refusal only blocks the *managed binary download*; the pip SDK bridge
is the supported cross-platform path and works headless on Linux. This unblocks the §10 "cheap
Linux-container future" **now** — one Linux VM can host many `Xvfb + Tryton GTK client + SDK bridge`
containers, no Windows license, no GCP-Windows detour. The Windows-on-GCP plan (§4–§6) is no longer
the only option.

## Scripts
- `holo_linux_patch.py` — the keyboard fix (import before bridge start; no-op off Linux).
- `driver_test.py` — proves screenshot/mouse/keyboard/shell/file-IO on the raw driver under Xvfb.
- `backend_test.py` — isolates pynput (MISSING) vs pyautogui (LANDED) vs xdotool (LANDED).
- `e2e_test.py` — full Holo3 cloud session driving the headless desktop; writes the sentinel.
- `auth_test.py` — confirms the key authenticates to both US + EU from inside Linux.
