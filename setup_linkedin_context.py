#!/usr/bin/env python3
"""
One-time LinkedIn authentication setup for Browserbase.

Run this once to create a persistent browser context, log into LinkedIn
manually, then save the context ID to .env for all future scrapes.

Usage:
    python3 setup_linkedin_context.py
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY", "")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID", "")
BROWSERBASE_API_BASE = "https://api.browserbase.com/v1"

if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
    print("ERROR: BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID must be set in .env")
    sys.exit(1)

HEADERS = {
    "X-BB-API-Key": BROWSERBASE_API_KEY,
    "Content-Type": "application/json"
}


def create_context() -> str:
    print("\n[1/4] Creating persistent Browserbase context...")
    resp = requests.post(
        f"{BROWSERBASE_API_BASE}/contexts",
        json={"projectId": BROWSERBASE_PROJECT_ID},
        headers=HEADERS,
        timeout=15
    )
    resp.raise_for_status()
    context_id = resp.json()["id"]
    print(f"      ✓ Context created: {context_id}")
    return context_id


def create_auth_session(context_id: str) -> dict:
    print("\n[2/4] Opening browser session with persistent context...")
    resp = requests.post(
        f"{BROWSERBASE_API_BASE}/sessions",
        json={
            "projectId": BROWSERBASE_PROJECT_ID,
            "keepAlive": True,
            "browserSettings": {
                "context": {
                    "id": context_id,
                    "persist": True
                }
            }
        },
        headers=HEADERS,
        timeout=15
    )
    resp.raise_for_status()
    session = resp.json()
    print(f"      ✓ Session created: {session['id']}")
    return session


def navigate_to_linkedin(session: dict) -> None:
    """Use Playwright to navigate to LinkedIn login page in the live session."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("      [!] Playwright not installed — open the live URL manually in your browser.")
        return

    connect_url = session.get("connectUrl")
    if not connect_url:
        return

    print("\n[3/4] Navigating browser to LinkedIn login page...")
    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(connect_url)
        try:
            ctx = browser.contexts[0] if browser.contexts else browser.new_context()
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(1500)
            print("      ✓ Browser navigated to LinkedIn login page.")
        finally:
            browser.close()


def stop_session(session_id: str) -> None:
    requests.put(
        f"{BROWSERBASE_API_BASE}/sessions/{session_id}",
        json={"projectId": BROWSERBASE_PROJECT_ID, "status": "REQUEST_RELEASE"},
        headers=HEADERS,
        timeout=15
    )


def save_context_to_env(context_id: str) -> None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        env_path = ".env"

    set_key(env_path, "BROWSERBASE_LINKEDIN_CONTEXT_ID", context_id)
    print(f"\n[4/4] ✓ Saved BROWSERBASE_LINKEDIN_CONTEXT_ID={context_id} to {env_path}")


def main():
    print("=" * 65)
    print(" 🔐 Browserbase LinkedIn Authentication Setup")
    print("=" * 65)
    print("\nThis script creates a persistent browser context and lets you")
    print("log into LinkedIn once. All future scrapes reuse this auth.")

    # Step 1: Create persistent context
    context_id = create_context()

    # Step 2: Open session
    session = create_auth_session(context_id)
    session_id = session["id"]
    live_url = f"https://www.browserbase.com/sessions/{session_id}"

    # Step 3: Navigate to LinkedIn
    navigate_to_linkedin(session)

    # Step 4: Ask user to log in
    print(f"\n{'=' * 65}")
    print(" ACTION REQUIRED — Please log into LinkedIn:")
    print(f"{'=' * 65}")
    print(f"\n  Open this URL in your browser to see and interact with the")
    print(f"  remote browser session:\n")
    print(f"  👉 {live_url}\n")
    print(f"  Log in with your LinkedIn credentials in that browser window.")
    print(f"  Once logged in, come back here and press ENTER.\n")

    input("  Press ENTER after you have logged into LinkedIn... ")

    # Step 5: Stop session (context + cookies persist)
    print("\n  Saving session and stopping browser...")
    stop_session(session_id)
    time.sleep(2)

    # Step 6: Save context_id to .env
    save_context_to_env(context_id)

    print("\n" + "=" * 65)
    print(f" ✅ LinkedIn auth setup complete!")
    print(f"    Context ID: {context_id}")
    print(f"    All LinkedIn scrapes will now use this authenticated context.")
    print("=" * 65)


if __name__ == "__main__":
    main()
