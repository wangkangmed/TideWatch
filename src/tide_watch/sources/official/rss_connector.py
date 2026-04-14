"""通过 RSS/Atom 拉取官网公开更新（无需各厂商 API Key）。"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import feedparser
import httpx

from tide_watch.models.ids import SourceRef
from tide_watch.models.raw import RawFetchBatch, RawRecord
from tide_watch.sources.protocols import FetchCursor, SourceConnector

DEFAULT_USER_AGENT = "TideWatch/0.1 (information-acquisition; +https://github.com/)"


@dataclass
class RssCursor:
    """增量游标占位；后续可存 last_link / etag。"""

    last_link: str | None = None

    def to_checkpoint_blob(self) -> dict[str, Any]:
        return {"last_link": self.last_link}

    @classmethod
    def from_checkpoint_blob(cls, blob: dict[str, Any]) -> RssCursor:
        return cls(last_link=blob.get("last_link"))


def _entry_published_at(entry: Any) -> datetime:
    if getattr(entry, "published_parsed", None):
        return datetime.fromtimestamp(time.mktime(entry.published_parsed), tz=timezone.utc)
    if getattr(entry, "updated_parsed", None):
        return datetime.fromtimestamp(time.mktime(entry.updated_parsed), tz=timezone.utc)
    raw = getattr(entry, "published", None) or getattr(entry, "updated", None)
    if isinstance(raw, str):
        try:
            return parsedate_to_datetime(raw).astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            pass
    return datetime.now(timezone.utc)


def _entry_external_id(entry: Any, fallback: str) -> str:
    for attr in ("id", "guid"):
        val = getattr(entry, attr, None)
        if val:
            if hasattr(val, "value"):
                return str(val.value)
            return str(val)
    link = getattr(entry, "link", None)
    if link:
        return str(link)
    return fallback


class RssOfficialConnector(SourceConnector):
    """单一 RSS 源：OpenAI / Anthropic / Google AI 等官网 feed。"""

    def __init__(self, provider_id: str, feed_url: str, *, max_items: int = 8) -> None:
        self.provider_id = provider_id
        self.feed_url = feed_url
        self.max_items = max(1, max_items)

    async def fetch(self, scope: dict[str, Any], cursor: FetchCursor | None) -> RawFetchBatch:
        headers = {
            "User-Agent": scope.get("http_user_agent") or DEFAULT_USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
        }
        timeout = float(scope.get("http_timeout_sec", 45.0))
        async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            body = resp.text

        parsed = feedparser.parse(body)
        if getattr(parsed, "bozo", False) and not getattr(parsed, "entries", None):
            raise ValueError(f"RSS 解析失败: {getattr(parsed, 'bozo_exception', 'unknown')}")

        entries = list(parsed.entries or [])[: self.max_items]
        records: list[RawRecord] = []
        for i, entry in enumerate(entries):
            eid = _entry_external_id(entry, f"entry-{i}")
            title = getattr(entry, "title", None) or ""
            summary = (
                getattr(entry, "summary", None)
                or getattr(entry, "description", None)
                or getattr(entry, "subtitle", None)
                or ""
            )
            link = getattr(entry, "link", None) or ""
            text = summary.strip() or title.strip()
            pub = _entry_published_at(entry)
            ref = SourceRef(provider_id=self.provider_id, external_id=eid[:512])
            idem = f"rss:{self.provider_id}:{eid[:400]}"
            records.append(
                RawRecord(
                    source_ref=ref,
                    fetched_at=pub,
                    mime_type="application/rss-item+xml",
                    text=text,
                    metadata={
                        "title": title,
                        "url": link,
                        "feed_url": self.feed_url,
                    },
                    idempotency_key=idem,
                )
            )

        batch_id = f"{self.provider_id}-{uuid.uuid4().hex[:12]}"
        return RawFetchBatch(batch_id=batch_id, records=records, errors=[])

    def merge_cursor(self, previous: FetchCursor | None, batch: RawFetchBatch) -> FetchCursor | None:
        return None
