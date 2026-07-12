"""Does the DRIVER's own keyboard path (pyautogui/pynput via XTEST) land text in a focused xterm on Xvfb?"""
import subprocess, time, os
from pathlib import Path
from hai_drivers.desktop.local import LocalDesktopDriver

out = Path("/tmp/kbd_landed.txt")
if out.exists(): out.unlink()

d = LocalDesktopDriver()
# focus the xterm window explicitly via xdotool so focus is not the variable under test
wid = subprocess.check_output(["xdotool","search","--name","xterm"]).split()[0].decode()
subprocess.run(["xdotool","windowactivate","--sync",wid])
subprocess.run(["xdotool","windowfocus","--sync",wid])
print("active window:", subprocess.check_output(["xdotool","getactivewindow"]).decode().strip(), "target:", wid)
time.sleep(0.5)

# Use the DRIVER's own write()/tap_key() — the exact path the bridge uses.
d.write("echo DRIVER_KBD_LANDED > /tmp/kbd_landed.txt", delay_between_keys=0.02)
d.tap_key("enter")
time.sleep(1.0)

print("result:", out.read_text().strip() if out.exists() else "MISSING — driver keystrokes did NOT land")
