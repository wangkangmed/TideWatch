"""社交流 HTTP 辅助：有限重试，不做反爬绕过。"""

from __future__ import annotations

import time
from typing import Any, Callable

import httpx

DEFAULT_TIMEOUT = 20.0
DEFAULT_UA = "TideWatch-SocialIngest/1.0 (+https://github.com/tidewatch)"


def http_get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    max_retries_429: int = 2,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    """GET JSON；对 429 做指数退避重试。"""
    h = {"User-Agent": DEFAULT_UA, "Accept": "application/json"}
    if headers:
        h.update(headers)
    attempt = 0
    while True:
        with httpx.Client(timeout=timeout, follow_redirects=True, headers=h) as client:
            resp = client.get(url, params=params)
        if resp.status_code == 429 and attempt < max_retries_429:
            sleep_fn(2**attempt)
            attempt += 1
            continue
        resp.raise_for_status()
        return resp.json()
