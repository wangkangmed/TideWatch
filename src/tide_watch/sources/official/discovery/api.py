"""REST list endpoint discovery（official transport: rest_api）。"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.discovery.network_utils import (
    classify_network_error,
    get_url_text,
    url_host_resolvable,
)
from tide_watch.sources.official.source_definitions import CandidateURL, OfficialTransportConfig, SourceDefinition

logger = logging.getLogger(__name__)

_DEFAULT_FIELD_MAP = {"url": "url", "title": "title", "summary": "summary", "id": "id"}


def _compose_list_url(strategy: OfficialTransportConfig, source: SourceDefinition) -> str:
    if strategy.url:
        return str(strategy.url).strip()
    b = (strategy.base_url or "").strip().rstrip("/")
    p = (strategy.list_path or "").strip().lstrip("/")
    if b and p:
        return f"{b}/{p}"
    if b:
        return b
    return (source.api_list_url or "").strip()


def _merge_headers(source: SourceDefinition, strategy: OfficialTransportConfig) -> dict[str, str]:
    h = dict(source.api_headers or {})
    h.update(strategy.headers or {})
    return h


def _traverse_items(data: Any, items_path: str | None) -> list[Any]:
    if items_path:
        cur: Any = data
        for part in items_path.split("."):
            if isinstance(cur, dict):
                cur = cur.get(part)
            else:
                return []
        return cur if isinstance(cur, list) else []

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("items", "data", "results", "records", "entries"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    return []


def _pick_field(row: Any, logical: str, field_map: dict[str, str]) -> Any:
    key = field_map.get(logical) or _DEFAULT_FIELD_MAP.get(logical) or logical
    if not isinstance(row, dict):
        return None
    cur: Any = row
    for part in str(key).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def discover_from_rest_api(
    company: str,
    source: SourceDefinition,
    strategy: OfficialTransportConfig,
    *,
    max_items: int = 50,
    max_retries: int = 2,
) -> list[CandidateURL]:
    list_url = _compose_list_url(strategy, source)
    if not list_url:
        return []
    settings = TideWatchSettings()
    if settings.official_dns_precheck and not url_host_resolvable(list_url):
        return []

    items_path = strategy.items_path or source.api_items_path
    field_map = {**_DEFAULT_FIELD_MAP, **(source.api_field_map or {}), **(strategy.field_map or {})}
    # Try strategy/source headers first, then generic UA fallback.
    text = ""
    last_err: str | None = None
    headers = _merge_headers(source, strategy)
    for pass_idx in range(2):
        try:
            time.sleep(0.05)
            if pass_idx == 0 and headers:
                resp = httpx.get(list_url, headers=headers, timeout=25.0, follow_redirects=True)
                resp.raise_for_status()
                text = resp.text
            else:
                text = get_url_text(
                    list_url,
                    timeout=float(settings.official_http_timeout_sec),
                    user_agent="TideWatch-Official-REST/1.0",
                    retries=max(max_retries, int(settings.official_http_retries)),
                )
            if text:
                break
        except Exception as exc:  # noqa: BLE001
            last_err = f"{classify_network_error(exc)}:{exc}"
            logger.warning("rest_api_fetch_fail source=%s url=%s pass=%s err=%s", source.id, list_url, pass_idx, exc)
    if not text:
        logger.info("rest_api_empty source=%s url=%s err=%s", source.id, list_url, last_err)
        return []

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("rest_api_json_parse_error source=%s url=%s", source.id, list_url)
        return []

    rows = _traverse_items(payload, items_path)
    out: list[CandidateURL] = []
    now = datetime.now(timezone.utc)
    for idx, row in enumerate(rows[:max_items]):
        if not isinstance(row, dict):
            continue
        link = _pick_field(row, "url", field_map)
        if link is None:
            for alt in ("link", "href", "permalink", "webUrl"):
                if isinstance(row.get(alt), str):
                    link = row[alt]
                    break
        if isinstance(link, dict) and isinstance(link.get("href"), str):
            link = urljoin(list_url, link["href"])
        if not isinstance(link, str) or not link.strip():
            continue
        if not link.startswith("http"):
            link = urljoin(list_url, link)
        title = _pick_field(row, "title", field_map)
        summary = _pick_field(row, "summary", field_map)
        ext_id = _pick_field(row, "id", field_map)
        meta = {
            "transport": "rest_api",
            "list_endpoint": list_url,
            "raw_item": row,
        }
        out.append(
            CandidateURL(
                source_id=source.id,
                company=company,
                url=link.strip(),
                discovered_at=now,
                source_type=source.type,
                hint_doc_type="article",
                priority=95 - min(idx, 90),
                metadata={
                    "title": title if isinstance(title, str) else None,
                    "snippet": summary if isinstance(summary, str) else None,
                    "external_id": ext_id,
                    **meta,
                },
            )
        )
    return out
