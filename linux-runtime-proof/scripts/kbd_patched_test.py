import subprocess, time
from pathlib import Path
import holo_linux_patch  # applies the monkeypatch on import
from hai_drivers.desktop.local import LocalDesktopDriver

out = Path("/tmp/kbd_patched.txt")
if out.exists(): out.unlink()
d = LocalDesktopDriver()
wid = subprocess.check_output(["xdotool","search","--name","xterm"]).split()[0].decode()
subprocess.run(["xdotool","windowactivate","--sync",wid]); subprocess.run(["xdotool","windowfocus","--sync",wid])
time.sleep(0.3)
d.write("echo DRIVER_KBD_PATCHED > /tmp/kbd_patched.txt", delay_between_keys=0.02)
d.tap_key("enter")
time.sleep(1.0)
print("PATCHED driver keyboard:", out.read_text().strip() if out.exists() else "STILL MISSING")
