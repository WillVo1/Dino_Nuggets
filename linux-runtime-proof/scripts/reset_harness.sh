#!/bin/bash
# Runs INSIDE the container. Proves the demo reset primitive:
#   - baseline (bare desktop) captured while clean
#   - after a "task" opens GUI apps + dirties $HOME, reset:
#       * kills the GUI apps
#       * leaves Xvfb + window manager + the (stand-in) SDK bridge ALIVE
#         => the bridge's session_id would survive
#       * restores $HOME to the pristine baseline
# The reset/capture logic is injected via $RESET_SCRIPT / $CAPTURE_SCRIPT env
# vars holding the VERBATIM bytes from web/backend/app/reset.py.
set -u
FAIL=0
note() { echo "  $*"; }
check() { if eval "$2"; then echo "PASS: $1"; else echo "FAIL: $1"; FAIL=1; fi; }

export HOME_DIR=/home/agent
export BASELINE=/opt/agent/home-baseline.tgz
export KILL_PROCS="slack chrome chromium firefox xterm soffice"

# --- fresh bare-desktop home -------------------------------------------------
rm -rf "$HOME_DIR"; mkdir -p "$HOME_DIR" /opt/agent
echo "pristine" > "$HOME_DIR/.config_marker"    # a dotfile that belongs in baseline

# --- X stack + a stand-in for the long-poll SDK bridge -----------------------
Xvfb :99 -screen 0 1280x800x24 -nolisten tcp >/tmp/xvfb.log 2>&1 &
XVFB_PID=$!
export DISPLAY=:99
sleep 2
openbox >/tmp/openbox.log 2>&1 &
WM_PID=$!
sleep 0.5
# The real SDK bridge is a python process long-polling the cloud; a named sleep
# is a faithful stand-in for "a non-GUI process that must survive the reset".
bash -c 'exec -a hai-bridge sleep 3600' &
BRIDGE_PID=$!
sleep 0.5

echo "=== capture baseline (bare desktop) ==="
bash -c "$CAPTURE_SCRIPT" || { echo "FAIL: capture returned nonzero"; exit 1; }
check "baseline tarball exists" '[ -f "$BASELINE" ]'

echo "=== simulate a task: open apps + dirty \$HOME ==="
# plain xterm keeps a live shell -> persists as both an X window and a process
xterm &
xterm &
# wait (up to ~5s) for the windows to actually map, so the post-reset
# "windows closed" assertion is meaningful rather than trivially true
for _ in $(seq 1 25); do
  [ "$(xdotool search --name xterm 2>/dev/null | wc -l | tr -d ' ')" -ge 2 ] && break
  sleep 0.2
done
echo "left over from last run" > "$HOME_DIR/task_output.txt"
rm -f "$HOME_DIR/.config_marker"                 # task clobbered a baseline dotfile
WIN_BEFORE=$(xdotool search --name xterm 2>/dev/null | wc -l | tr -d ' ')
note "windows before reset: $WIN_BEFORE"
check "task actually opened windows (>=2)" "[ \"$WIN_BEFORE\" -ge 2 ]"
note "task_output.txt present: $([ -f "$HOME_DIR/task_output.txt" ] && echo yes || echo no)"

echo "=== RESET ==="
bash -c "$RESET_SCRIPT"; RC=$?
check "reset exit code 0" "[ $RC -eq 0 ]"
sleep 1

echo "=== assertions ==="
check "all xterm windows closed"        '[ "$(xdotool search --name xterm 2>/dev/null | wc -l | tr -d " ")" = "0" ]'
check "no xterm processes remain"       '! pgrep -x xterm >/dev/null'
check "Xvfb still alive (display kept)" "kill -0 $XVFB_PID 2>/dev/null"
check "window manager still alive"      "kill -0 $WM_PID 2>/dev/null"
check "SDK bridge still alive (=> session_id survives)" "kill -0 $BRIDGE_PID 2>/dev/null"
check "task_output.txt removed"         '[ ! -f "$HOME_DIR/task_output.txt" ]'
check "baseline dotfile restored"       '[ -f "$HOME_DIR/.config_marker" ]'
check "restored dotfile content intact" '[ "$(cat "$HOME_DIR/.config_marker")" = "pristine" ]'

# --- negative path: a CORRUPT baseline must fail loudly and NOT wipe $HOME ----
# (this is the review's #1 finding — the old script wiped $HOME then printed
#  RESET_OK regardless of whether the restore actually succeeded)
echo "=== RESET with a corrupt baseline ==="
echo "user data that must survive a failed reset" > "$HOME_DIR/precious.txt"
GOOD_BAK=/opt/agent/home-baseline.good.tgz
cp "$BASELINE" "$GOOD_BAK"
head -c 32 /dev/urandom > "$BASELINE"            # truncate/garble the tarball
bash -c "$RESET_SCRIPT" >/tmp/reset_bad.out 2>&1; BAD_RC=$?
note "corrupt-reset rc=$BAD_RC"
check "corrupt reset exits nonzero"      "[ $BAD_RC -ne 0 ]"
check "corrupt reset did NOT print RESET_OK" '! grep -q RESET_OK /tmp/reset_bad.out'
check "user data preserved on failed reset"  '[ -f "$HOME_DIR/precious.txt" ]'
check "no leftover staging dir"          '[ -z "$(find "$HOME_DIR" -maxdepth 1 -name ".reset-stage.*" 2>/dev/null)" ]'
cp "$GOOD_BAK" "$BASELINE"                        # restore good baseline

echo
if [ $FAIL -eq 0 ]; then echo "ALL RESET CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
kill $XVFB_PID $WM_PID $BRIDGE_PID 2>/dev/null
exit $FAIL
