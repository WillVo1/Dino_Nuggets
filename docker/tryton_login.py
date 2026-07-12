#!/usr/bin/env python3
"""Auto-login into Tryton ERP desktop client using pyautogui.

The Tryton client shows a login dialog with a profile dropdown.
If the profile is pre-configured (via tryton.conf), we just need to:
1. Click "Connect" on the profile
2. Type "admin" in the password field (empty field, pyautogui works)
3. Click OK

Usage: python3 tryton_login.py <server:port>
"""
import sys
import time
import pyautogui

def login_to_tryton(server: str = "localhost:8000") -> bool:
    """Click through the Tryton login dialog."""
    # Disable pyautogui failsafe (mouse to corner = abort)
    pyautogui.FAILSAFE = False

    print("[tryton_login] waiting for Tryton window to appear...")
    time.sleep(3)

    # Take a screenshot to see what we're working with
    try:
        img = pyautogui.screenshot()
        print(f"[tryton_login] screenshot size: {img.size}")
    except Exception as e:
        print(f"[tryton_login] screenshot failed: {e}")

    # The Tryton login dialog has a "Connect" button.
    # With the pre-configured profile, it should show "local" profile.
    # Click in the center area where the profile list usually is.
    print("[tryton_login] clicking on profile area...")
    pyautogui.click(640, 400)
    time.sleep(1)

    # Double-click the profile to connect
    print("[tryton_login] double-clicking profile to connect...")
    pyautogui.doubleClick(640, 400)
    time.sleep(3)

    # Take screenshot to see what happened
    img = pyautogui.screenshot()
    # Check if we got a password dialog
    # The password dialog is usually a small window in the center

    # Type the password (admin) — this works because the field is empty
    print("[tryton_login] typing password...")
    pyautogui.click(640, 450)  # Click in the password field area
    time.sleep(0.5)
    pyautogui.write("admin", interval=0.05)
    time.sleep(0.3)

    # Press Enter or click OK
    print("[tryton_login] pressing Enter to confirm...")
    pyautogui.press("enter")
    time.sleep(3)

    # Take final screenshot
    img = pyautogui.screenshot()
    print(f"[tryton_login] final screenshot size: {img.size}")

    # Check if we're logged in by looking for the main Tryton window
    # (it has a menu tree on the left)
    # For now just report success
    print("[tryton_login] login attempt complete")
    return True


if __name__ == "__main__":
    server = sys.argv[1] if len(sys.argv) > 1 else "localhost:8000"
    login_to_tryton(server)
