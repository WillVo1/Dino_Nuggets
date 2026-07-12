#!/usr/bin/env python3
"""Pre-authenticate Slack in Chromium by injecting the xoxc token into localStorage.

Slack's web app stores the auth token in localStorage under key "localConfig_v2"
and the token format is "xoxc-...". We set this before Chromium loads slack.com
so the app starts already logged in.

Usage: python3 slack_auth.py <xoxc-token>
"""
import sys
import os
import json
import sqlite3
import glob

def setup_chromium_slack_auth(token: str) -> None:
    """Create a Chromium profile with Slack auth pre-baked."""
    profile_dir = os.path.expanduser("~/.config/chromium/Default")
    os.makedirs(profile_dir, exist_ok=True)

    # Write a localStorage entry for slack.com with the token
    # Chromium stores localStorage in a leveldb database.
    # We'll use a simpler approach: write a Preferences file that
    # triggers a cookie/localStorage restore on first load.

    # Write the token to a file that Chromium's --load-extension can use
    # Actually, the simplest approach: set the Slack token as a cookie
    # Slack uses the token in localStorage, not cookies.

    # Create the localStorage leveldb directory
    ls_dir = os.path.join(profile_dir, "Local Storage", "leveldb")
    os.makedirs(ls_dir, exist_ok=True)

    # Write a simple log file that leveldb will pick up
    # The key is "slack:localConfig" and value contains the token
    # We'll use the "CURRENT" file to point to our log

    # Actually, the most reliable approach: use a Chromium extension
    # that sets localStorage on app.slack.com. But that's complex.
    #
    # Simpler: just create a HTML file that sets localStorage and redirect,
    # then have Chromium load that instead of app.slack.com directly.

    auth_html = f"""<!DOCTYPE html>
<html>
<head><title>Setting up Slack...</title></head>
<body>
<p>Setting up Slack authentication...</p>
<script>
// Set the Slack token in localStorage
localStorage.setItem('localConfig_v2', JSON.stringify({{
    "token": "{token}",
    "teams": {{}}
}}));

// Also try setting it as a cookie
document.cookie = "d={token}; domain=.slack.com; path=/; secure";

// Redirect to Slack
window.location.href = 'https://app.slack.com';
</script>
</body>
</html>"""

    auth_path = "/tmp/slack_auth.html"
    with open(auth_path, "w") as f:
        f.write(auth_html)

    print(f"[slack_auth] Auth HTML written to {auth_path}")

    # Also set environment variable so Chromium can use it
    os.environ["SLACK_AUTH_URL"] = f"file://{auth_path}"

    # Create a user script that will be loaded by Chromium
    # Write to the Chromium user data dir
    user_scripts_dir = os.path.join(profile_dir, "User Scripts")
    os.makedirs(user_scripts_dir, exist_ok=True)

    # Write a content script that injects the token
    script = f"""
// Slack auth injection script
console.log("Injecting Slack token...");
try {{
    localStorage.setItem('localConfig_v2', JSON.stringify({{
        "token": "{token}",
        "teams": {{}}
    }}));
}} catch(e) {{
    console.error("Failed to set token:", e);
}}
"""

    script_path = os.path.join(user_scripts_dir, "slack_auth.js")
    with open(script_path, "w") as f:
        f.write(script)

    print(f"[slack_auth] User script written to {script_path}")
    print(f"[slack_auth] Token: {token[:20]}...")

    # Return the auth HTML path so the entrypoint can use it
    with open("/tmp/slack_auth_url.txt", "w") as f:
        f.write(f"file://{auth_path}")

    print("[slack_auth] Done")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: slack_auth.py <xoxc-token>")
        sys.exit(1)

    token = sys.argv[1]
    setup_chromium_slack_auth(token)
