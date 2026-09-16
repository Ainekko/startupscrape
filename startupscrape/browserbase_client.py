import logging
import time
from typing import Optional, Dict, Any, List
import requests

from .config import (
    BROWSERBASE_API_KEY,
    BROWSERBASE_PROJECT_ID,
    BROWSERBASE_API_BASE,
    DEFAULT_TIMEOUT
)

logger = logging.getLogger(__name__)


class BrowserbaseClient:
    """Client for Browserbase headless browser cloud sessions with persistent context support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_id: Optional[str] = None
    ):
        self.api_key = api_key or BROWSERBASE_API_KEY
        self.project_id = project_id or BROWSERBASE_PROJECT_ID
        self.headers = {
            "X-BB-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    # ──────────────────────────────────────────────
    # Context management
    # ──────────────────────────────────────────────

    def create_context(self) -> Dict[str, Any]:
        """Create a new persistent browser context (survives across sessions)."""
        url = f"{BROWSERBASE_API_BASE}/contexts"
        payload = {"projectId": self.project_id}
        resp = requests.post(url, json=payload, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[Browserbase] Context created: {data['id']}")
        return data

    def list_contexts(self) -> List[Dict[str, Any]]:
        """List all existing persistent contexts."""
        url = f"{BROWSERBASE_API_BASE}/contexts"
        resp = requests.get(url, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # ──────────────────────────────────────────────
    # Session management
    # ──────────────────────────────────────────────

    def create_session(self, context_id: Optional[str] = None, keep_alive: bool = False) -> Dict[str, Any]:
        """
        Create a new Browserbase browser session.
        If context_id is provided, the session reuses that persistent context (auth, cookies etc.).
        If keep_alive is True, the session won't auto-terminate when the CDP connection drops.
        """
        payload: Dict[str, Any] = {"projectId": self.project_id}

        if keep_alive:
            payload["keepAlive"] = True

        if context_id:
            payload["browserSettings"] = {
                "context": {
                    "id": context_id,
                    "persist": True
                }
            }

        resp = requests.post(
            f"{BROWSERBASE_API_BASE}/sessions",
            json=payload,
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"[Browserbase] Session created: {data['id']}")
        return data

    def stop_session(self, session_id: str) -> None:
        """Explicitly stop a Browserbase session."""
        try:
            requests.put(
                f"{BROWSERBASE_API_BASE}/sessions/{session_id}",
                json={"projectId": self.project_id, "status": "REQUEST_RELEASE"},
                headers=self.headers,
                timeout=DEFAULT_TIMEOUT
            )
            logger.info(f"[Browserbase] Session stopped: {session_id}")
        except Exception as e:
            logger.warning(f"[Browserbase] Failed to stop session {session_id}: {e}")

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get status and details of a session."""
        resp = requests.get(
            f"{BROWSERBASE_API_BASE}/sessions/{session_id}",
            headers=self.headers,
            timeout=DEFAULT_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()

    def get_session_live_url(self, session_id: str) -> str:
        """Return the Browserbase live view URL for a session (for manual interaction)."""
        return f"https://www.browserbase.com/sessions/{session_id}"

    # ──────────────────────────────────────────────
    # Scraping
    # ──────────────────────────────────────────────

    def scrape_url(
        self,
        url: str,
        context_id: Optional[str] = None,
        wait_selector: Optional[str] = None,
        wait_ms: int = 3000,
        timeout_ms: int = 30000
    ) -> Dict[str, str]:
        """
        Launch a remote browser session on Browserbase, navigate to url,
        extract rendered HTML and body text, then stop the session.
        If context_id is provided the session is authenticated with that context.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed, falling back to direct HTTP.")
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=DEFAULT_TIMEOUT)
            return {"html": resp.text, "text": resp.text}

        session = self.create_session(context_id=context_id)
        session_id = session["id"]
        connect_url = session.get("connectUrl")
        if not connect_url:
            self.stop_session(session_id)
            raise RuntimeError(f"No connectUrl in session response: {session}")

        extracted = {"html": "", "text": ""}
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(connect_url)
                try:
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    page = context.pages[0] if context.pages else context.new_page()

                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

                    if wait_selector:
                        try:
                            page.wait_for_selector(wait_selector, timeout=8000)
                        except Exception:
                            pass

                    page.wait_for_timeout(wait_ms)

                    extracted["html"] = page.content()
                    try:
                        extracted["text"] = page.inner_text("body")
                    except Exception:
                        extracted["text"] = ""
                finally:
                    browser.close()
        finally:
            self.stop_session(session_id)

        return extracted
