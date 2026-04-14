"""Fetcher implementations for different access modes."""

from __future__ import annotations

import time
from typing import Callable

import httpx

from tide_watch.models.ingestion import FetchPlan, FetchResult

DEFAULT_TIMEOUT_SEC = 20.0
DEFAULT_USER_AGENT = "TideWatch-Ingestion/1.0 (+focused-subgraph)"


def _subset_headers(headers: httpx.Headers) -> dict[str, str]:
    keep = {"content-type", "server", "cf-ray", "location", "cache-control"}
    out: dict[str, str] = {}
    for key, val in headers.items():
        lk = key.lower()
        if lk in keep:
            out[lk] = val
    return out


def _base_result(plan: FetchPlan) -> FetchResult:
    return FetchResult(
        source_id=plan.source_id,
        company=plan.company,
        url=plan.url,
        fetch_mode=plan.mode,
        success=False,
    )


def direct_html_fetcher(plan: FetchPlan, client: httpx.Client) -> FetchResult:
    result = _base_result(plan)
    try:
        resp = client.get(plan.url)
        result.final_url = str(resp.url)
        result.status_code = resp.status_code
        result.content_type = resp.headers.get("content-type")
        result.headers = _subset_headers(resp.headers)
        result.raw_html = resp.text
        result.raw_text = resp.text
    except httpx.TimeoutException as exc:
        result.error = f"timeout: {exc!s}"
    except Exception as exc:  # noqa: BLE001
        result.error = str(exc)
    return result


def feed_fetcher(plan: FetchPlan, client: httpx.Client) -> FetchResult:
    return direct_html_fetcher(plan, client)


def listing_fetcher(plan: FetchPlan, client: httpx.Client) -> FetchResult:
    return direct_html_fetcher(plan, client)


def metadata_fetcher(plan: FetchPlan, _client: httpx.Client) -> FetchResult:
    result = _base_result(plan)
    result.status_code = 200
    result.content_type = "application/x.metadata"
    result.raw_text = ""
    result.success = True
    result.discovered_metadata = {"metadata_only": True}
    return result


def rendered_html_fetcher(plan: FetchPlan, client: httpx.Client) -> FetchResult:
    # Optional path; fallback to direct fetch unless a real renderer is wired.
    return direct_html_fetcher(plan, client)


def skip_fetcher(plan: FetchPlan, _client: httpx.Client) -> FetchResult:
    result = _base_result(plan)
    result.status_code = 204
    result.success = True
    result.raw_text = ""
    result.discovered_metadata = {"skipped": True}
    return result


def run_fetch_plan(
    plan: FetchPlan,
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    user_agent: str = DEFAULT_USER_AGENT,
    max_retries_429: int = 2,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> FetchResult:
    transport = {
        "direct_html": direct_html_fetcher,
        "rendered_html": rendered_html_fetcher,
        "api": direct_html_fetcher,
        "listing_only": listing_fetcher,
        "feed_only": feed_fetcher,
        "metadata_only": metadata_fetcher,
        "skip": skip_fetcher,
    }
    fetcher = transport[plan.mode]
    with httpx.Client(
        timeout=timeout_sec,
        follow_redirects=True,
        headers={"User-Agent": user_agent, "Accept": "text/html,application/xml;q=0.9,*/*;q=0.8"},
    ) as client:
        attempt = 0
        while True:
            result = fetcher(plan, client)
            if result.status_code != 429 or attempt >= max_retries_429:
                return result
            sleep_fn(2**attempt)
            attempt += 1
