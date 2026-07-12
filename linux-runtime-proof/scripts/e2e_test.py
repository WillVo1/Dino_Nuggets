"""End-to-end: real Holo3 cloud session drives a headless Linux desktop via the pip SDK bridge.

Proof-of-drive: we ask Holo to open a terminal (xterm) and type a command that
writes a sentinel file. If the file appears with the exact contents, the CLOUD
brain actually drove THIS Linux desktop through the pure-python bridge.
"""
import os, sys, time, traceback
from pathlib import Path
from hai_agents import Client
from hai_agents.environment import HaiAgentsEnvironment
from hai_agents.types.agent import Agent
from hai_agents.types.environment import Environment_Desktop

SENTINEL = Path("/tmp/holo_proof.txt")
if SENTINEL.exists():
    SENTINEL.unlink()

key = os.environ["HAI_API_KEY"]
region = HaiAgentsEnvironment.US if os.environ.get("HAI_REGION","US")=="US" else HaiAgentsEnvironment.EU
client = Client(api_key=key, environment=region, timeout=120)

agent = Agent(
    name="linux-desktop-probe",
    description="Drives the local Linux desktop to prove SDK bridge works headless.",
    environments=[Environment_Desktop(id="desktop", host="user_device")],
    instructions=(
        "You control a Linux desktop. An xterm terminal is already open and focused. "
        "Click into the xterm window, then type exactly this command and press Enter:\n"
        "echo HOLO_DROVE_LINUX > /tmp/holo_proof.txt\n"
        "Then report DONE."
    ),
)

print(f"[e2e] region={region.name} starting session (auto-bridge spawns PyautoguiDesktopBridge)…", flush=True)
t0 = time.time()
try:
    result = client.run_session(
        agent=agent,
        messages="Open the terminal and write the proof file as instructed.",
        max_steps=12,
        max_time_s=180,
        wait_for_seconds=20,
    )
    print(f"[e2e] session finished in {time.time()-t0:.1f}s")
    print("[e2e] status:", getattr(result, "status", "?"))
    ans = getattr(result, "answer", None) or getattr(result, "final_answer", None)
    print("[e2e] answer:", str(ans)[:400])
except Exception as e:
    print("[e2e] session error:", type(e).__name__, str(e)[:600])
    traceback.print_exc()

time.sleep(1)
if SENTINEL.exists():
    print(f"\n✅ PROOF FILE PRESENT: {SENTINEL.read_text()!r}")
    print("==> The H Company CLOUD agent drove the LOCAL headless Linux desktop via the pip SDK. No hai-agent-runtime binary involved.")
else:
    print("\n(no sentinel file — see session output above for how far it got)")
