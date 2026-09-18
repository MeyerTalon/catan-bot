"""Tests for the per-ip rate limiter and client ip selection."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from app.core.rate_limit import RateLimiter, client_ip


def _request(xff: str | None, peer: str = '10.0.0.9') -> Any:
    """Build a minimal request stub with the given X-Forwarded-For header.

    Args:
        xff: Header value, or None to omit it.
        peer: Peer address reported by the server.

    Returns:
        Object with `.headers` and `.client.host`.
    """
    request = MagicMock()
    request.headers = {'x-forwarded-for': xff} if xff else {}
    request.client.host = peer
    return request


def test_client_ip_uses_peer_without_trusted_proxies() -> None:
    assert client_ip(_request('1.1.1.1'), trusted_proxy_hops=0) == '10.0.0.9'


def test_client_ip_ignores_client_supplied_prefix() -> None:
    # the client forged "6.6.6.6"; cloudfront then the alb appended the real chain
    xff = '6.6.6.6, 203.0.113.7, 130.176.0.1'
    assert client_ip(_request(xff), trusted_proxy_hops=2) == '203.0.113.7'


def test_client_ip_single_hop_edge() -> None:
    assert client_ip(_request('203.0.113.7'), trusted_proxy_hops=1) == '203.0.113.7'


def test_client_ip_falls_back_to_peer_when_header_too_short() -> None:
    assert client_ip(_request(None), trusted_proxy_hops=2) == '10.0.0.9'


def test_rate_limiter_blocks_after_limit_and_resets_next_window() -> None:
    limiter = RateLimiter(limit=2, window_seconds=60)
    assert limiter.hit('a', now=0)
    assert limiter.hit('a', now=1)
    assert not limiter.hit('a', now=2)
    assert limiter.hit('b', now=2)
    assert limiter.hit('a', now=61)
