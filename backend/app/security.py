"""
app/security.py — Lightweight Bot Guard, Scanner Detection, and In-Memory Rate Limiting
========================================================================================
Fast, defensive protections without heavy external dependencies.
Protects login and sensitive endpoints against brute force, automated credential stuffing,
and vulnerability scanners.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from typing import Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Known aggressive automated bot & attack scanner tokens in User-Agent
BLOCKED_USER_AGENTS = (
    "sqlmap",
    "nikto",
    "masscan",
    "zgrab",
    "gobuster",
    "dirbuster",
    "wpscan",
    "havij",
    "acunetix",
    "nessus",
)

# Rate limiting thresholds
MAX_LOGIN_FAILURES = 5
FAIL_WINDOW_SECONDS = 300       # 5 minutes window
BLOCK_DURATION_SECONDS = 300    # 5 minutes block on repeated failures


class SecurityGuard:
    """Thread-safe in-memory security manager for rate limiting and bot detection."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._blocks: dict[str, float] = {}
        self._request_history: dict[str, list[float]] = defaultdict(list)

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extract the true client IP behind Render/Cloudflare/reverse proxies."""
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()

        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "127.0.0.1"

    @classmethod
    def verify_request_hygiene(cls, request: Request) -> None:
        """
        Check request headers for bot/scanner signatures.
        Rejects empty user agents or known malicious penetration scanners.
        """
        ua = (request.headers.get("User-Agent") or "").strip().lower()

        # Reject empty or whitespace-only User-Agent on auth endpoints
        if not ua:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request headers: User-Agent is required.",
            )

        # Reject known scanner signatures
        for token in BLOCKED_USER_AGENTS:
            if token in ua:
                logger.warning("Blocked scanner request matching '%s' from %s", token, cls.get_client_ip(request))
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied by security policy.",
                )

    def check_login_rate_limit(self, ip: str) -> None:
        """Verify whether an IP is currently blocked due to repeated failed logins."""
        now = time.time()
        with self._lock:
            blocked_until = self._blocks.get(ip)
            if blocked_until:
                if now < blocked_until:
                    remaining = int(blocked_until - now)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Too many failed login attempts. Please wait {remaining} seconds before trying again.",
                        headers={"Retry-After": str(remaining)},
                    )
                else:
                    del self._blocks[ip]

    def record_login_failure(self, ip: str) -> None:
        """Record a failed login attempt; activate temporary block if threshold is crossed."""
        now = time.time()
        with self._lock:
            # Prune failures older than window
            history = [t for t in self._failures[ip] if now - t < FAIL_WINDOW_SECONDS]
            history.append(now)
            self._failures[ip] = history

            if len(history) >= MAX_LOGIN_FAILURES:
                self._blocks[ip] = now + BLOCK_DURATION_SECONDS
                self._failures[ip].clear()
                logger.warning("IP %s temporarily blocked for %d seconds after %d failed login attempts",
                               ip, BLOCK_DURATION_SECONDS, MAX_LOGIN_FAILURES)

    def record_login_success(self, ip: str) -> None:
        """Reset failed attempt counters on valid authentication."""
        with self._lock:
            self._failures.pop(ip, None)
            self._blocks.pop(ip, None)

    def check_endpoint_rate_limit(self, ip: str, endpoint: str, max_requests: int = 60, window: int = 60) -> None:
        """Lightweight sliding window rate limiter for general endpoints."""
        now = time.time()
        key = f"{ip}:{endpoint}"
        with self._lock:
            history = [t for t in self._request_history[key] if now - t < window]
            if len(history) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Request rate limit exceeded. Please throttle requests.",
                    headers={"Retry-After": str(window)},
                )
            history.append(now)
            self._request_history[key] = history


# Global security guard singleton
security_guard = SecurityGuard()

