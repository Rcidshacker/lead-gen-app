"""Per-domain token-bucket rate limiter."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Optional


class _TokenBucket:
    """Classic token-bucket implementation for a single domain.

    Args:
        rate: Tokens replenished per second.
        capacity: Maximum number of burst tokens.
    """

    __slots__ = ("rate", "capacity", "tokens", "last_refill", "_lock")

    def __init__(self, rate: float, capacity: Optional[float] = None) -> None:
        self.rate = max(rate, 0.01)  # Prevent zero/negative rate
        self.capacity = capacity if capacity is not None else rate * 5
        self.tokens = self.capacity  # Start full
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        """Add tokens based on elapsed time since last refill."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

    def acquire(self, timeout: Optional[float] = None) -> bool:
        """Consume one token, blocking until available or *timeout* elapses.

        Args:
            timeout: Maximum seconds to wait (``None`` = wait forever).

        Returns:
            ``True`` if a token was acquired, ``False`` on timeout.
        """
        deadline: Optional[float] = None
        if timeout is not None:
            deadline = time.monotonic() + timeout

        while True:
            with self._lock:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True

            # Not enough tokens — wait
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                time.sleep(min(0.05, remaining))
            else:
                time.sleep(0.05)

    def try_acquire(self) -> bool:
        """Non-blocking attempt to consume one token.

        Returns:
            ``True`` if a token was acquired, ``False`` otherwise.
        """
        with self._lock:
            self._refill()
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
        return False

    @property
    def available_tokens(self) -> float:
        """Current number of available tokens (approximate)."""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """Per-domain token-bucket rate limiter.

    Each domain gets its own independent token bucket so that scraping
    different sites does not unnecessarily slow down other pipelines.

    Example::

        limiter = RateLimiter(default_rate=2.0)   # 2 req/s by default
        limiter.set_rate("linkedin.com", 0.5)      # more conservative
        await limiter.acquire("linkedin.com")       # blocks if needed
        if limiter.try_acquire("indeed.com"):       # non-blocking
            ...
    """

    def __init__(
        self,
        default_rate: float = 2.0,
        default_capacity: Optional[float] = None,
    ) -> None:
        """Initialise the rate limiter.

        Args:
            default_rate: Default requests-per-second for new domains.
            default_capacity: Default burst capacity.  Defaults to
                ``rate * 5``.
        """
        self._default_rate = max(default_rate, 0.01)
        self._default_capacity = default_capacity
        self._buckets: dict[str, _TokenBucket] = {}
        self._global_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self, domain: str, timeout: Optional[float] = None) -> bool:
        """Block until a token is available for *domain*.

        Args:
            domain: The domain key (e.g. ``"linkedin.com"``).
            timeout: Maximum seconds to wait.  ``None`` blocks indefinitely.

        Returns:
            ``True`` if a token was acquired, ``False`` on timeout.
        """
        bucket = self._get_or_create_bucket(domain)
        return bucket.acquire(timeout=timeout)

    def try_acquire(self, domain: str) -> bool:
        """Non-blocking attempt to acquire a token for *domain*.

        Args:
            domain: The domain key.

        Returns:
            ``True`` if a token was available and consumed.
        """
        bucket = self._get_or_create_bucket(domain)
        return bucket.try_acquire()

    def set_rate(self, domain: str, rate: float) -> None:
        """Configure the rate for a specific domain.

        If the domain already has a bucket it is replaced with a new one
        initialised at full capacity.

        Args:
            domain: The domain key.
            rate: Requests per second.
        """
        with self._global_lock:
            bucket = _TokenBucket(
                rate=rate,
                capacity=self._default_capacity,
            )
            self._buckets[domain] = bucket

    def get_rate(self, domain: str) -> float:
        """Return the current rate for *domain*, or the default if unknown."""
        with self._global_lock:
            bucket = self._buckets.get(domain)
            return bucket.rate if bucket else self._default_rate

    def remove_domain(self, domain: str) -> None:
        """Remove the token bucket for *domain*."""
        with self._global_lock:
            self._buckets.pop(domain, None)

    @property
    def active_domains(self) -> list[str]:
        """List of domains that have been seen so far."""
        with self._global_lock:
            return list(self._buckets.keys())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create_bucket(self, domain: str) -> _TokenBucket:
        """Get the bucket for *domain*, creating it if necessary."""
        with self._global_lock:
            bucket = self._buckets.get(domain)
            if bucket is None:
                bucket = _TokenBucket(
                    rate=self._default_rate,
                    capacity=self._default_capacity,
                )
                self._buckets[domain] = bucket
            return bucket
