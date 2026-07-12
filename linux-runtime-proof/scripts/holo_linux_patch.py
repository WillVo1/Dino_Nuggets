"""Linux/Xvfb fix for hai-drivers LocalDesktopDriver.

Root cause (verified): the driver's mouse path uses pyautogui (lands on Xvfb),
but its keyboard path uses pynput's Controller, whose XTEST events do NOT land
in focused windows under Xvfb. pyautogui's keyboard DOES land. This monkeypatch
redirects write/press_key/release_key/tap_key/hotkey to pyautogui.

Import this module once before starting the bridge/session. Idempotent + no-op
off Linux, so it's safe to import everywhere.
"""
from __future__ import annotations
import sys

def apply() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    import pyautogui
    from hai_drivers.desktop.local.driver import LocalDesktopDriver

    if getattr(LocalDesktopDriver, "_holo_linux_kbd_patched", False):
        return True

    pyautogui.PAUSE = 0

    def write(self, text: str, delay_between_keys: float = 0.05) -> None:
        pyautogui.write(text, interval=max(delay_between_keys, 0.0))

    def press_key(self, key: str) -> None:
        pyautogui.keyDown(key)

    def release_key(self, key: str) -> None:
        pyautogui.keyUp(key)

    def tap_key(self, key: str) -> None:
        pyautogui.press(key)

    def hotkey(self, keys) -> None:
        pyautogui.hotkey(*list(keys))

    LocalDesktopDriver.write = write
    LocalDesktopDriver.press_key = press_key
    LocalDesktopDriver.release_key = release_key
    LocalDesktopDriver.tap_key = tap_key
    LocalDesktopDriver.hotkey = hotkey
    LocalDesktopDriver._holo_linux_kbd_patched = True
    return True

apply()
