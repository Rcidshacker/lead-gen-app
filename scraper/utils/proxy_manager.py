"""Thread-safe rotating proxy pool manager."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx
from loguru import logger


@dataclass
class ProxyEntry:
    """A single proxy with metadata.

    Attributes:
        url: The proxy URL (e.g., ``http://user:pass@host:port``).
        username: Proxy authentication username.
        password: Proxy authentication password.
        protocol: Proxy protocol — ``http``, ``https``, or ``socks5``.
        weight: Selection weight for weighted-random rotation.
        fail_count: Number of consecutive failures.
        cooldown_until: Unix timestamp until which the proxy is in cooldown.
    """

    url: str
    username: str = ""
    password: str = ""
    protocol: str = "http"
    weight: float = 1.0
    fail_count: int = 0
    cooldown_until: float = 0.0

    @property
    def is_available(self) -> bool:
        """Return ``True`` if the proxy is not in cooldown."""
        return time.time() >= self.cooldown_until

    def build_auth_url(self) -> str:
        """Build a full URL with embedded credentials."""
        if self.username and self.password:
            # Inject credentials into the URL
            # url is like http://host:port  →  http://user:pass@host:port
            if "@" not in self.url:
                parts = self.url.split("://", 1)
                if len(parts) == 2:
                    return f"{parts[0]}://{self.username}:{self.password}@{parts[1]}"
        return self.url


# Default cooldown duration: 60 seconds after a failure
_DEFAULT_COOLDOWN: float = 60.0
# Maximum consecutive failures before long cooldown
_MAX_FAIL_COUNT: int = 5
# Long cooldown: 10 minutes
_LONG_COOLDOWN: float = 600.0


class ProxyManager:
    """Thread-safe rotating proxy pool.

    Proxies are selected using weighted random rotation.  Failed proxies are
    temporarily moved to cooldown so they are not retried immediately.

    Example::

        proxies = [
            {"url": "http://proxy1:8080", "username": "u", "password": "p"},
            {"url": "http://proxy2:8080"},
        ]
        manager = ProxyManager(proxies)
        proxy_url = manager.get_proxy()
        manager.mark_bad(proxy_url)
    """

    def __init__(
        self,
        proxies: Optional[list[dict[str, Any]]] = None,
        default_cooldown: float = _DEFAULT_COOLDOWN,
        max_fail_count: int = _MAX_FAIL_COUNT,
        long_cooldown: float = _LONG_COOLDOWN,
        validate_timeout: float = 10.0,
    ) -> None:
        """Initialise the proxy manager.

        Args:
            proxies: A list of dicts, each containing at least ``url`` and
                optionally ``username``, ``password``, ``protocol``, and ``weight``.
            default_cooldown: Seconds to cooldown a proxy after a failure.
            max_fail_count: After this many consecutive failures the proxy
                receives a longer cooldown.
            long_cooldown: Extended cooldown for repeatedly failing proxies.
            validate_timeout: Timeout in seconds for health-check HEAD requests.
        """
        self._default_cooldown = default_cooldown
        self._max_fail_count = max_fail_count
        self._long_cooldown = long_cooldown
        self._validate_timeout = validate_timeout
        self._lock = threading.Lock()

        self._entries: list[ProxyEntry] = []
        if proxies:
            for p in proxies:
                self._add_entry(p)

        logger.info(
            f"ProxyManager initialised with {len(self._entries)} proxy(ies)"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_proxy(self) -> str:
        """Return a proxy URL using weighted random selection.

        Only proxies that are not in cooldown are considered.  If all proxies
        are in cooldown the cooldown is reset and one is chosen anyway.

        Returns:
            A proxy URL string (with embedded credentials if configured).
        """
        with self._lock:
            available = [e for e in self._entries if e.is_available]

            if not available:
                # All proxies are cooling down — reset and pick any
                logger.warning("All proxies in cooldown; resetting cooldowns")
                for entry in self._entries:
                    entry.cooldown_until = 0.0
                available = list(self._entries)

            if not available:
                return ""

            # Weighted random selection
            weights = [e.weight for e in available]
            chosen = random.choices(available, weights=weights, k=1)[0]
            return chosen.build_auth_url()

    def mark_bad(self, proxy_url: str) -> None:
        """Mark a proxy as failed and move it to cooldown.

        Args:
            proxy_url: The proxy URL (must match an entry's URL).
        """
        with self._lock:
            entry = self._find_entry_by_url(proxy_url)
            if entry is None:
                logger.warning(f"mark_bad: unknown proxy {proxy_url}")
                return

            entry.fail_count += 1
            if entry.fail_count >= self._max_fail_count:
                entry.cooldown_until = time.time() + self._long_cooldown
                logger.warning(
                    f"Proxy {entry.url} hit {entry.fail_count} failures — "
                    f"long cooldown ({self._long_cooldown}s)"
                )
            else:
                entry.cooldown_until = time.time() + self._default_cooldown
                logger.info(
                    f"Proxy {entry.url} marked bad — cooldown "
                    f"({self._default_cooldown}s)"
                )

    def mark_good(self, proxy_url: str) -> None:
        """Reset the failure counter for a proxy.

        Call this after a successful request to clear the failure state.

        Args:
            proxy_url: The proxy URL to reset.
        """
        with self._lock:
            entry = self._find_entry_by_url(proxy_url)
            if entry is None:
                return
            if entry.fail_count > 0:
                logger.info(f"Proxy {entry.url} marked good — resetting failures")
            entry.fail_count = 0
            entry.cooldown_until = 0.0

    async def validate_proxy(self, proxy_url: str) -> bool:
        """Health-check a proxy via an HTTP HEAD request.

        Args:
            proxy_url: The proxy URL to validate.

        Returns:
            ``True`` if the proxy is reachable and returned a 2xx status.
        """
        try:
            async with httpx.AsyncClient(
                proxy=proxy_url,
                timeout=self._validate_timeout,
            ) as client:
                resp = await client.head(
                    "https://httpbin.org/status/200",
                    follow_redirects=True,
                )
                ok = 200 <= resp.status_code < 300
                if ok:
                    self.mark_good(proxy_url)
                else:
                    self.mark_bad(proxy_url)
                return ok
        except Exception as exc:
            logger.debug(f"Proxy validation failed for {proxy_url}: {exc}")
            self.mark_bad(proxy_url)
            return False

    def add_proxy(self, proxy_dict: dict[str, Any]) -> None:
        """Add a proxy entry at runtime.

        Args:
            proxy_dict: Dict with at least ``url`` and optional auth fields.
        """
        with self._lock:
            self._add_entry(proxy_dict)
            logger.info(f"Added proxy: {proxy_dict.get('url', '?')}")

    @property
    def available_count(self) -> int:
        """Number of proxies not currently in cooldown."""
        with self._lock:
            return sum(1 for e in self._entries if e.is_available)

    @property
    def total_count(self) -> int:
        """Total number of registered proxies."""
        with self._lock:
            return len(self._entries)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_entry(self, proxy_dict: dict[str, Any]) -> None:
        """Create a :class:`ProxyEntry` and append it to the pool."""
        entry = ProxyEntry(
            url=proxy_dict.get("url", ""),
            username=str(proxy_dict.get("username", "")),
            password=str(proxy_dict.get("password", "")),
            protocol=proxy_dict.get("protocol", "http"),
            weight=float(proxy_dict.get("weight", 1.0)),
        )
        self._entries.append(entry)

    def _find_entry_by_url(self, proxy_url: str) -> Optional[ProxyEntry]:
        """Look up an entry by URL (stripped of credentials for matching)."""
        for entry in self._entries:
            if entry.url in proxy_url or proxy_url in entry.build_auth_url():
                return entry
        return None
