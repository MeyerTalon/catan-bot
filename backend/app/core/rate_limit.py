"""Fixed-window, per-client-ip rate limiting for the auth endpoints.

the app runs as a single task, so an in-process counter is enough; a second
task would double the effective limit, which is still a useful brake on
credential stuffing and sign-up floods.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


def client_ip(request: Request, trusted_proxy_hops: int) -> str:
    """Pick the client ip from X-Forwarded-For, ignoring anything the client could forge.

    each trusted proxy appends the address it saw to X-Forwarded-For, so the
    real client is `trusted_proxy_hops` entries from the right; everything
    left of that was supplied by the client and is untrusted.

    Args:
        request: Incoming request.
        trusted_proxy_hops: Number of proxies that appended to the header.

    Returns:
        Best-effort client ip, or the peer address when no proxies are trusted.
    """
    peer = request.client.host if request.client else 'unknown'
    if trusted_proxy_hops <= 0:
        return peer
    forwarded = [
        part.strip()
        for part in request.headers.get('x-forwarded-for', '').split(',')
        if part.strip()
    ]
    if len(forwarded) < trusted_proxy_hops:
        return peer
    return forwarded[len(forwarded) - trusted_proxy_hops]


class RateLimiter:
    """Count requests per key inside fixed windows.

    Attributes:
        limit: Requests allowed per key per window.
        window_seconds: Window length in seconds.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[tuple[str, int], int] = defaultdict(int)
        self._lock = threading.Lock()

    def hit(self, key: str, now: float | None = None) -> bool:
        """Record one request and report whether it is within the limit.

        Args:
            key: Client identifier (ip).
            now: Current time; defaults to time.time(). exposed for tests.

        Returns:
            True when the request is allowed, False when the limit is exceeded.
        """
        current = now if now is not None else time.time()
        window = int(current // self.window_seconds)
        with self._lock:
            # drop counters from earlier windows so the dict cannot grow unbounded
            for stale in [k for k in self._hits if k[1] < window]:
                del self._hits[stale]
            self._hits[(key, window)] += 1
            return self._hits[(key, window)] <= self.limit


def rate_limited(limit: int, window_seconds: int = 60) -> Callable[[Request], None]:
    """Build a FastAPI dependency that enforces a per-ip request limit.

    Args:
        limit: Requests allowed per client ip per window.
        window_seconds: Window length in seconds.

    Returns:
        Dependency that raises 429 once the limit is exceeded.
    """
    limiter = RateLimiter(limit, window_seconds)

    def dependency(request: Request) -> None:
        """Reject the request with 429 when its client ip is over the limit.

        Args:
            request: Incoming request.

        Raises:
            HTTPException: 429 when the limit is exceeded.
        """
        key = client_ip(request, get_settings().trusted_proxy_hops)
        if not limiter.hit(key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests. Try again in a minute.',
                headers={'Retry-After': str(window_seconds)},
            )

    return dependency
