"""Network helpers for official discovery and listing expansion."""

from __future__ import annotations

import socket
import time
from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

import httpx

NetworkErrorKind = Literal["dns", "timeout", "tls", "http_status", "connection", "unknown"]


def classify_network_error(exc: Exception) -> NetworkErrorKind:
    msg = str(exc).lower()
    if isinstance(exc, httpx.TimeoutException) or "timed out" in msg:
        return "timeout"
    if "name or service not known" in msg or "temporary failure in name resolution" in msg:
        return "dns"
    if "certificate" in msg or "ssl" in msg or "tls" in msg:
        return "tls"
    if isinstance(exc, httpx.HTTPStatusError):
        return "http_status"
    if isinstance(exc, httpx.ConnectError) or "connection" in msg:
        return "connection"
    return "unknown"


@lru_cache(maxsize=256)
def can_resolve_host(hostname: str) -> bool:
    if not hostname:
        return False
    try:
        socket.getaddrinfo(hostname, None)
        return True
    except OSError:
        return False


def url_host_resolvable(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return can_resolve_host(host)


def get_url_text(
    url: str,
    *,
    timeout: float,
    user_agent: str,
    retries: int = 1,
) -> str:
    last: Exception | None = None
    for attempt in range(max(1, retries) + 1):
        try:
            resp = httpx.get(
                url,
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": user_agent, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"},
            )
            resp.raise_for_status()
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt >= retries:
                break
            kind = classify_network_error(exc)
            if kind in {"dns", "tls", "http_status"}:
                break
            time.sleep(0.15 * (attempt + 1))
    assert last is not None
    raise last
