import logging
from typing import Optional, Dict, Any
import requests

from .config import (
    BROWSERBASE_API_KEY,
    BROWSERBASE_PROJECT_ID,
    BROWSERBASE_API_BASE,
    DEFAULT_TIMEOUT
)

logger = logging.getLogger(__name__)


class BrowserbaseClient:
    """Client for Browserbase headless browser cloud infrastructure with stealth & proxies."""

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

    def create_session(self, proxies: bool = True) -> Dict[str, Any]:
        """Create a new Browserbase browser session."""
        url = f"{BROWSERBASE_API_BASE}/sessions"
        payload = {
            "projectId": self.project_id,
            "proxies": proxies
        }
        resp = requests.post(url, json=payload, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get status and details of an existing session."""
        url = f"{BROWSERBASE_API_BASE}/sessions/{session_id}"
        resp = requests.get(url, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def scrape_url(self, url: str, wait_selector: Optional[str] = None, timeout_ms: int = 30000) -> Dict[str, str]:
        """
        Launch a remote stealth browser on Browserbase, navigate to target URL,
        and extract rendered HTML and inner text.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright not installed, falling back to direct HTTP requests.")
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=DEFAULT_TIMEOUT)
            return {"html": resp.text, "text": resp.text}

        session = self.create_session(proxies=True)
        connect_url = session.get("connectUrl")
        if not connect_url:
            raise RuntimeError(f"Failed to obtain connectUrl from Browserbase: {session}")

        extracted = {"html": "", "text": ""}
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(connect_url)
            try:
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = context.pages[0] if context.pages else context.new_page()

                # Stealth navigation
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=5000)
                    except Exception:
                        pass
                else:
                    page.wait_for_timeout(2000)

                extracted["html"] = page.content()
                try:
                    extracted["text"] = page.inner_text("body")
                except Exception:
                    extracted["text"] = ""
            finally:
                browser.close()

        return extracted
