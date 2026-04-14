"""Reddit：公开 .json 端点，无 OAuth 的最小可用路径。"""

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

_REDDIT_ROOT = "https://www.reddit.com"


def _dt_from_utc(ts: Any) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _post_to_candidate(source: SocialSourceConfig, d: dict[str, Any], *, discovered_at: datetime) -> SocialCandidateItem:
    pid = str(d.get("id") or "")
    permalink = str(d.get("permalink") or "")
    url = f"{_REDDIT_ROOT}{permalink}" if permalink.startswith("/") else str(d.get("url") or permalink)
    return SocialCandidateItem(
        source_id=source.source_id,
        platform="reddit",
        source_type=source.source_type,
        external_id=f"t3_{pid}" if pid and not pid.startswith("t3_") else pid,
        url=url,
        author_handle=str(d.get("author") or "") or None,
        title=str(d.get("title") or "") or None,
        text=str(d.get("selftext") or "") or "",
        summary=None,
        published_at=_dt_from_utc(d.get("created_utc")),
        discovered_at=discovered_at,
        engagement={"score": d.get("score"), "num_comments": d.get("num_comments")},
        metadata={"subreddit": d.get("subreddit"), "permalink": permalink},
    )


class RedditConnector(SocialConnector):
    platform = "reddit"

    def discover(
        self,
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> tuple[list[SocialCandidateItem], SocialCheckpoint | None]:
        now = datetime.now(timezone.utc)
        st = source.source_type.lower()
        limit = max(1, min(source.max_items, 100))
        after = (checkpoint.blob.get("after") if checkpoint else None) if checkpoint else None
        out: list[SocialCandidateItem] = []
        try:
            if st == "subreddit_feed":
                sub = (source.handle_or_community or "").strip().lstrip("r/")
                if not sub:
                    return [], checkpoint
                params: dict[str, Any] = {"raw_json": "1", "limit": limit}
                if after:
                    params["after"] = after
                data = http_get_json(f"{_REDDIT_ROOT}/r/{sub}/new.json", params=params)
            elif st == "search":
                q = (source.query or "").strip()
                if not q:
                    return [], checkpoint
                params = {"raw_json": "1", "limit": limit, "q": q, "sort": "relevance"}
                if after:
                    params["after"] = after
                data = http_get_json(f"{_REDDIT_ROOT}/search.json", params=params)
            elif st == "thread_detail":
                thread = (source.query or source.handle_or_community or "").strip()
                if not thread:
                    return [], checkpoint
                post_id = thread
                if "comments/" in thread:
                    # https://www.reddit.com/r/x/comments/abc123/title/
                    parts = thread.split("comments/")
                    if len(parts) > 1:
                        post_id = parts[1].split("/")[0]
                data = http_get_json(f"{_REDDIT_ROOT}/comments/{post_id}.json", params={"raw_json": "1", "limit": 1})
            else:
                logger.warning("reddit unsupported source_type=%s source=%s", st, source.source_id)
                return [], checkpoint

            if st == "thread_detail":
                listings = data if isinstance(data, list) else []
                if not listings:
                    return [], checkpoint
                children = (listings[0] or {}).get("data", {}).get("children") or []
                for ch in children:
                    if (ch or {}).get("kind") != "t3":
                        continue
                    d = (ch or {}).get("data") or {}
                    if d.get("name", "").startswith("t3_") or d.get("id"):
                        out.append(_post_to_candidate(source, d, discovered_at=now))
                new_cp = SocialCheckpoint(source_id=source.source_id, platform="reddit", blob={})
                return out, new_cp

            children = (data.get("data") or {}).get("children") or []
            next_after = (data.get("data") or {}).get("after")
            for ch in children:
                if (ch or {}).get("kind") != "t3":
                    continue
                d = (ch or {}).get("data") or {}
                if not d.get("id"):
                    continue
                out.append(_post_to_candidate(source, d, discovered_at=now))
            new_cp = SocialCheckpoint(
                source_id=source.source_id,
                platform="reddit",
                blob={"after": next_after} if next_after else {},
            )
            return out, new_cp
        except Exception as exc:  # noqa: BLE001
            logger.warning("reddit_discover_failed source=%s err=%s", source.source_id, exc)
            return [], checkpoint

    def enrich(
        self,
        items: list[SocialCandidateItem],
        source: SocialSourceConfig,
        checkpoint: SocialCheckpoint | None,
    ) -> RawFetchBatch:
        if not items:
            return RawFetchBatch(batch_id=f"social-reddit-{source.source_id}-empty", records=[], errors=[])

        merged: list[SocialCandidateItem] = []
        errors: list[str] = []
        for item in items:
            try:
                if not source.include_comments:
                    merged.append(item)
                    continue
                post_id = item.external_id.removeprefix("t3_")
                data = http_get_json(f"{_REDDIT_ROOT}/comments/{post_id}.json", params={"raw_json": "1", "limit": 24})
                listings = data if isinstance(data, list) else []
                comment_lines: list[str] = []
                if len(listings) > 1:
                    cchildren = (listings[1].get("data") or {}).get("children") or []
                    for ch in cchildren[:12]:
                        cd = (ch or {}).get("data") or {}
                        body = str(cd.get("body") or "").strip()
                        author = str(cd.get("author") or "")
                        if body and body not in {"[deleted]", "[removed]"}:
                            comment_lines.append(f"- @{author}: {body[:500]}")
                new_meta = dict(item.metadata)
                new_meta["comment_context"] = "\n".join(comment_lines)
                text = item.text
                if comment_lines:
                    text = (text or "").strip() + "\n\n--- comments ---\n" + "\n".join(comment_lines)
                merged.append(
                    item.model_copy(
                        update={
                            "text": text,
                            "metadata": new_meta,
                        }
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(f"reddit_enrich:{item.external_id}:{exc!s}")
                if source.metadata_fallback:
                    merged.append(item)

        return enriched_candidates_to_raw_batch(
            merged,
            source=source,
            batch_id=f"social-reddit-{source.source_id}",
            errors=errors,
        )
