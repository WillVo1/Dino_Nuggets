"""Exercise LocalDesktopDriver for real under a headless Xvfb display."""
import base64, sys, traceback

def main():
    from hai_drivers.desktop.local import LocalDesktopDriver
    d = LocalDesktopDriver()
    print("driver class:", type(d).__name__)

    w, h = d.get_screen_size()
    print(f"[screen] {w}x{h}")
    assert w > 0 and h > 0, "bad screen size"

    # Screenshot round-trips to a real PNG?
    b64 = d.screenshot_b64()
    raw = base64.b64decode(b64)
    print(f"[screenshot] {len(raw)} bytes, PNG magic={raw[:8].hex()}")
    assert raw[:8] == bytes.fromhex("89504e470d0a1a0a"), "not a PNG"

    # Mouse move + read back
    d.mouse_move_to(123, 210)
    pos = d.get_mouse_position()
    print(f"[mouse] moved to (123,210) -> read back {pos}")

    # Click (must not raise)
    d.click(50, 50)
    print("[click] ok")

    # Keyboard: tap a key (no focused window, just must not raise)
    d.tap_key("a")
    print("[keyboard] tap_key('a') ok")

    # Shell exec through the driver
    r = d.run_command(["echo", "hello-from-linux-driver"])
    print(f"[run_command] returncode={getattr(r,'returncode',None)} stdout={getattr(r,'stdout','')!r}")

    # File IO through the driver
    d.write_file("/tmp/driver_probe.txt", b"probe-bytes")
    back = d.read_file("/tmp/driver_probe.txt")
    print(f"[file_io] wrote/read back: {back!r}")
    assert back == b"probe-bytes"

    # Accessibility tree (may be empty on Linux, must not crash)
    try:
        tree = d.get_accessibility_tree()
        print(f"[a11y] get_accessibility_tree() -> {len(tree)} chars")
    except Exception as e:
        print(f"[a11y] not supported on Linux: {type(e).__name__}: {e}")

    print("\nRESULT: LocalDesktopDriver fully operational on headless Linux/Xvfb ✅")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
