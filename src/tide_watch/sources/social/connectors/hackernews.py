"""Hacker News：官方 Firebase API + Algolia 公开搜索 API。"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from tide_watch.models.raw import RawFetchBatch
from tide_watch.sources.social.connectors.base import SocialConnector
from tide_watch.sources.social.http_utils import http_get_json
from tide_watch.sources.social.models import SocialCandidateItem, SocialCheckpoint, SocialSourceConfig
from tide_watch.sources.social.normalizers import enriched_candidates_to_raw_batch

logger = logging.getLogger(__name__)

_HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
_HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
_HN_NEW = "https://hacker-news.firebaseio.com/v0/newstories.json"
_HN_ALGOLIA = "https://hn.algolia.com/api/v1/search"


def _dt_from_epoch(ts: Any) -> datetime | None:
    """支持秒级 Unix 与毫秒时间戳。"""
    if ts is None:
        return None
    try:
        v = float(ts)
        if v > 1e12:  # 毫秒
            v = v / 1000.0
        return datetime.fromtimestamp(v, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class HackerNewsConnector(SocialConnector):
    platform = "hackernews"

    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        now = datetime.now(timezone.utc)
        st = source.source_type.lower()
        limit = max(1, min(source.max_items, 50))
        last_seen = int(checkpoint.blob.get("last_max_id") or 0) if checkpoint else 0
        out: list[SocialCandidateItem] = []
        try:
            if st in {"search"}:
                q = (source.query or "").strip()
                if not q:
                    return [], checkpoint
                data = http_get_json(
                    _HN_ALGOLIA,
                    params={"query": q, "tags": "story", "hitsPerPage": limit},
                )
                hits = data.get("hits") or []
                max_id = last_seen
                for h in hits:
                    hid = int(h.get("objectID") or 0)
                    max_id = max(max_id, hid)
                    url = str(h.get("url") or "") or f"https://news.ycombinator.com/item?id={hid}"
                    out.append(
                        SocialCandidateItem(
                            source_id=source.source_id,
                            platform="hackernews",
                            source_type=st,
                            external_id=str(hid),
                            url=url,
                            author_handle=str(h.get("author") or "") or None,
                            title=str(h.get("title") or "") or None,
                            text="",
                            summary=None,
                            published_at=_dt_from_epoch(h.get("created_at_i")),
                            discovered_at=now,
                            engagement={"points": h.get("points"), "num_comments": h.get("num_comments")},
                            metadata={"hn_story_id": hid},
                        )
                    )
                new_cp = SocialCheckpoint(source_id=source.source_id, platform="hackernews", blob={"last_max_id": max_id})
                return out, new_cp

            if st in {"top_feed", "top", "new_feed", "new"}:
                listing_url = _HN_TOP if st in {"top_feed", "top"} else _HN_NEW
                ids: list[int] = http_get_json(listing_url)
                slice_ids = ids[:limit]
                max_id = max(slice_ids + [last_seen]) if slice_ids else last_seen
                for iid in slice_ids:
                    item = http_get_json(_HN_ITEM.format(id=iid))
                    if not isinstance(item, dict) or item.get("type") != "story":
                        continue
                    url = str(item.get("url") or "") or f"https://news.ycombinator.com/item?id={iid}"
                    out.append(
                        SocialCandidateItem(
                            source_id=source.source_id,
                            platform="hackernews",
                            source_type=st,
                            external_id=str(iid),
                            url=url,
                            author_handle=str(item.get("by") or "") or None,
                            title=str(item.get("title") or "") or None,
                            text=str(item.get("text") or "") if item.get("text") else "",
                            summary=None,
                            published_at=_dt_from_epoch(item.get("time")),
                            discovered_at=now,
                            engagement={"points": item.get("score"), "num_comments": item.get("descendants")},
                            metadata={"hn_story_id": iid},
                        )
                    )
                new_cp = SocialCheckpoint(source_id=source.source_id, platform="hackernews", blob={"last_max_id": max_id})
                return out, new_cp

            logger.warning("hackernews unsupported source_type=%s source=%s", st, source.source_id)
            return [], checkpoint
        except Exception as exc:  # noqa: BLE001
            logger.warning("hackernews_discover_failed source=%s err=%s", source.source_id, exc)
            return [], checkpoint

    def enrich(
        self,
        items: list[SocialCandidateItem],
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> RawFetchBatch:
        if not items:
            return enriched_candidates_to_raw_batch([], source=source, batch_id=f"social-hn-{source.source_id}", errors=[])

        merged: list[SocialCandidateItem] = []
        errors: list[str] = []
        for item in items:
            try:
                iid = int(item.external_id)
                detail = http_get_json(_HN_ITEM.format(id=iid))
                if not isinstance(detail, dict):
                    raise RuntimeError("invalid item payload")
                text = str(detail.get("text") or item.text or "")
                if detail.get("title"):
                    title = str(detail.get("title"))
                else:
                    title = item.title
                eng = {
                    "points": detail.get("score"),
                    "num_comments": detail.get("descendants"),
                }
                meta = dict(item.metadata)
                meta["kids"] = detail.get("kids") or []
                comment_lines: list[str] = []
                if source.include_comments and meta.get("kids"):
                    for kid in (meta["kids"])[:8]:
                        try:
                            c = http_get_json(_HN_ITEM.format(id=kid))
                        except Exception:  # noqa: BLE001
                            continue
                        if not isinstance(c, dict) or c.get("type") != "comment":
                            continue
                        body = str(c.get("text") or "").replace("<p>", "\n").strip()
                        who = str(c.get("by") or "")
                        if body:
                            comment_lines.append(f"- @{who}: {body[:400]}")
                meta["comment_context"] = "\n".join(comment_lines)
                full_text = (text or "").strip()
                if comment_lines:
                    full_text = full_text + "\n\n--- comments ---\n" + "\n".join(comment_lines)
                merged.append(
                    item.model_copy(
                        update={
                            "title": title,
                            "text": full_text,
                            "engagement": eng,
                            "metadata": meta,
                            "published_at": item.published_at,
                        }
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"hn_enrich:{item.external_id}:{exc!s}")
                if source.metadata_fallback:
                    merged.append(item)

        return enriched_candidates_to_raw_batch(
            merged,
            source=source,
            batch_id=f"social-hn-{source.source_id}",
            errors=errors,
        )
