"""Which input backend lands text in a focused xterm on Xvfb? Isolate pynput vs pyautogui vs xdotool."""
import subprocess, time, os
from pathlib import Path

def focus_xterm():
    wid = subprocess.check_output(["xdotool","search","--name","xterm"]).split()[0].decode()
    subprocess.run(["xdotool","windowactivate","--sync",wid])
    subprocess.run(["xdotool","windowfocus","--sync",wid])
    time.sleep(0.3)
    return wid

def probe(name, fn):
    p = Path(f"/tmp/{name}.txt")
    if p.exists(): p.unlink()
    focus_xterm()
    fn(name, p)
    time.sleep(1.0)
    print(f"  {name:16s}: {'LANDED ' + repr(p.read_text().strip()) if p.exists() else 'MISSING'}")

# 1) pynput (what the driver uses)
def via_pynput(name, p):
    from pynput.keyboard import Controller, Key
    kb = Controller()
    kb.type(f"echo {name} > {p}")
    kb.tap(Key.enter)

# 2) pyautogui
def via_pyautogui(name, p):
    import pyautogui
    pyautogui.write(f"echo {name} > {p}", interval=0.02)
    pyautogui.press("enter")

# 3) xdotool (known-good XTEST reference)
def via_xdotool(name, p):
    subprocess.run(["xdotool","type",f"echo {name} > {p}"])
    subprocess.run(["xdotool","key","Return"])

print("backend keystroke landing test (focused xterm on Xvfb):")
probe("pynput_typed", via_pynput)
probe("pyautogui_typed", via_pyautogui)
probe("xdotool_typed", via_xdotool)
