"""Content extraction with dates, aggregate detection, and metadata-rich fallbacks."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape

from tide_watch.web.date_parser import (
    parse_date_from_title_line,
    parse_dates_from_html,
    parse_feed_date_string,
    parse_first_date_from_changelog_text,
)
from tide_watch.web.block_classifier import is_challenge_block
from tide_watch.models.ingestion import ExtractedDocument, FetchResult
from tide_watch.sources.official.source_definitions import CandidateURL
from tide_watch.web.page_classifier import classify_html_page

_PROTECTED_FALLBACK_TITLES: dict[str, str] = {
    "openai_news": "OpenAI News",
    "openai_research": "OpenAI Research",
    "openai_product": "OpenAI Product releases",
    "openai_api_docs": "OpenAI Platform Docs",
    "xai_news": "xAI News",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_META_DESC_RE = re.compile(
    r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)
_CANONICAL_RE = re.compile(
    r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)


def _clean_text(text: str) -> str:
    stripped = _TAG_RE.sub(" ", text)
    stripped = unescape(stripped)
    return _WS_RE.sub(" ", stripped).strip()


def _parse_metadata_published(meta: dict) -> tuple[datetime | None, str | None]:
    raw = meta.get("published_at") or meta.get("date")
    if raw is None:
        return None, None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc), "metadata_datetime_object"
    s = str(raw).strip()
    dt = parse_feed_date_string(s) or _try_iso(s)
    return dt, "metadata_string" if dt else None


def _try_iso(s: str) -> datetime | None:
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def is_likely_aggregate_listing_page(html: str, url: str) -> tuple[bool, str]:
    """识别栏目 / 聚合 / 存档列表页，降低质量分。"""
    u = (url or "").lower()
    h = (html or "").lower()
    if "/content-type/" in u or "/topic/" in u or "/category/" in u:
        return True, "url_aggregation_path"
    if "archives page" in h or re.search(r"archive?s?\s+page\s+\d+", h, re.I):
        return True, "html_archives_title"
    if "cookie" in h and "onetrust" in h and len(_clean_text(html)) < 800:
        return True, "short_consent_shell"
    if u.count("/blog/") >= 1 and ("/page/" in u or re.search(r"page/\d+", u)):
        return True, "pagination_listing"
    return False, ""


def extract_document(candidate: CandidateURL, result: FetchResult) -> ExtractedDocument:
    metadata = dict(candidate.metadata or {})
    html = result.raw_html or result.raw_text or ""
    title = metadata.get("title")
    summary = metadata.get("snippet")
    canonical_url = candidate.url
    body_text = ""
    score = 0.2
    extracted_fields: dict = {}
    notes: list[str] = []

    pub_meta, meta_src = _parse_metadata_published(metadata)
    published_at: datetime | None = pub_meta
    if pub_meta and meta_src:
        extracted_fields["published_at_listing_metadata"] = str(metadata.get("published_at") or metadata.get("date"))
        notes.append(f"published_from_{meta_src}")

    updated_at: datetime | None = None

    if html:
        m_title = _TITLE_RE.search(html)
        if m_title and not title:
            title = _clean_text(m_title.group(1))
        m_desc = _META_DESC_RE.search(html)
        if m_desc and not summary:
            summary = _clean_text(m_desc.group(1))
        m_can = _CANONICAL_RE.search(html)
        if m_can:
            canonical_url = m_can.group(1).strip()
        pub_h, upd_h, fields_h, notes_h = parse_dates_from_html(html)
        extracted_fields.update(fields_h)
        notes.extend(notes_h)
        if pub_h and published_at is None:
            published_at = pub_h
        if upd_h:
            updated_at = upd_h

    if not title:
        title = candidate.url

    p_title, tsrc = parse_date_from_title_line(title)
    if p_title and published_at is None:
        published_at = p_title
        notes.append(f"published_from_{tsrc or 'title'}")

    if not published_at and html:
        pc, psrc = parse_first_date_from_changelog_text(_clean_text(html)[:8000])
        if pc:
            published_at = pc
            notes.append(f"published_from_{psrc or 'changelog_plain'}")

    cls = classify_html_page(
        html,
        candidate.url,
        title=title,
        block_type=result.detected_block_type,
        meta_description=summary,
    )
    extracted_fields["page_type"] = cls.page_type
    extracted_fields["page_signals"] = cls.page_signals
    notes.append(f"page_classified:{cls.page_type}")

    full_clean = _clean_text(html) if html else ""
    if cls.body_handling == "metadata_only":
        body_text = ""
        score = min(score, cls.quality_cap)
    elif cls.body_handling == "trimmed":
        base = cls.suggested_snippet or summary or full_clean
        body_text = (base or "")[:3500]
        score = min(score, cls.quality_cap)
    else:
        body_text = full_clean
        if len(body_text) > 120:
            score = min(0.7, cls.quality_cap)
        elif body_text:
            score = min(0.45, cls.quality_cap)

    agg, agg_reason = is_likely_aggregate_listing_page(html, candidate.url)
    if agg:
        score = min(score, 0.25)
        notes.append(f"aggregate_listing:{agg_reason}")
        extracted_fields["aggregate_listing"] = True
        extracted_fields["aggregate_reason"] = agg_reason
        if cls.page_type == "article_page":
            extracted_fields["page_type"] = "aggregation_page"
            body_text = (cls.suggested_snippet or summary or body_text)[:3200]

    if summary is None and body_text:
        summary = body_text[:280]

    is_agg_type = extracted_fields.get("page_type") in ("aggregation_page", "listing_page", "docs_shell_page")
    ing = {
        "detail_extract_success": bool(len(body_text or "") > 100 and not is_agg_type),
        "detail_fetch_attempt": True,
        "metadata_fallback": False,
    }
    meta_out = {
        **metadata,
        "fetch_mode": result.fetch_mode,
        "status_code": result.status_code,
        "ingestion": ing,
    }

    return ExtractedDocument(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        canonical_url=canonical_url,
        title=title,
        published_at=published_at,
        updated_at=updated_at,
        author=None,
        body_text=body_text,
        summary=summary,
        tags=[],
        language="en" if re.search(r"[a-zA-Z]", title or "") else None,
        outbound_links=[],
        extraction_quality_score=min(score, cls.quality_cap),
        extracted_fields=extracted_fields,
        extraction_notes=notes,
        raw_metadata=meta_out,
    )


def extract_listing_index_fallback(candidate: CandidateURL, result: FetchResult) -> ExtractedDocument:
    """listing_only 且仍为种子页时：从 HTML 再抽一条目列表写入摘要（单条文档）。"""
    from tide_watch.sources.official.discovery.listing_items import extract_listing_item_drafts
    from tide_watch.sources.official.source_definitions import SourceDefinition

    metadata = dict(candidate.metadata or {})
    html = result.raw_html or result.raw_text or ""
    sel = metadata.get("listing_selectors") or {}
    hdl_src = SourceDefinition(
        id=candidate.source_id,
        type=candidate.source_type,
        url=candidate.url,
        listing_selectors=sel if isinstance(sel, dict) else {},
    )
    drafts = extract_listing_item_drafts(candidate.url, html, source=hdl_src, max_items=20)
    lines = []
    for d in drafts[:18]:
        t = d.title or d.url
        lines.append(f"- {t} :: {d.url}")
    body_text = "\n".join(lines) if lines else _clean_text(html)[:4000]
    summary = (lines[0] if lines else "")[:400] if lines else _clean_text(html)[:280]
    title = metadata.get("title")
    if not title and html:
        m = _TITLE_RE.search(html)
        if m:
            title = _clean_text(m.group(1))
    if not title:
        title = candidate.url
    pub, upd, fields, notes = parse_dates_from_html(html)
    ing = {
        "detail_extract_success": False,
        "detail_fetch_attempt": False,
        "metadata_fallback": True,
        "listing_index_fallback": True,
    }
    fields = {**fields, "page_type": "listing_page"}
    return ExtractedDocument(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        canonical_url=candidate.url,
        title=title if isinstance(title, str) else candidate.url,
        published_at=pub,
        updated_at=upd,
        author=None,
        body_text=body_text,
        summary=summary,
        tags=[],
        language=None,
        outbound_links=[],
        extraction_quality_score=0.35 if lines else 0.22,
        extracted_fields=fields,
        extraction_notes=notes + ["listing_index_fallback"],
        raw_metadata={**metadata, "fetch_mode": result.fetch_mode, "status_code": result.status_code, "ingestion": ing},
    )


def metadata_rich_document(candidate: CandidateURL, result: FetchResult) -> ExtractedDocument:
    """metadata_only / 降级 / 无正文：合并候选元数据 + 响应 HTML 中的弱信号。"""
    metadata = dict(candidate.metadata or {})
    html = result.raw_html or result.raw_text or ""
    title = metadata.get("title") or metadata.get("detail_url")
    summary = metadata.get("snippet") or metadata.get("summary") or ""

    disp = metadata.get("display_name")
    if disp and (not title or title.strip() == candidate.url.strip()):
        title = disp
    elif (not title or title == candidate.url) and candidate.source_id in _PROTECTED_FALLBACK_TITLES:
        title = _PROTECTED_FALLBACK_TITLES[candidate.source_id]
    extracted_fields: dict = {}
    notes: list[str] = ["metadata_rich_document"]

    pub_meta, meta_src = _parse_metadata_published(metadata)
    published_at = pub_meta
    if pub_meta:
        extracted_fields["published_at_listing_metadata"] = str(metadata.get("published_at") or metadata.get("date"))
        notes.append(f"published_from_{meta_src}")

    updated_at: datetime | None = None
    if html:
        if not title:
            mo = _OG_TITLE_RE.search(html) or _TITLE_RE.search(html)
            if mo:
                title = _clean_text(mo.group(1))
        if not summary:
            md = _META_DESC_RE.search(html)
            if md:
                summary = _clean_text(md.group(1))
        pub_h, upd_h, fields_h, notes_h = parse_dates_from_html(html)
        extracted_fields.update(fields_h)
        notes.extend(notes_h)
        if pub_h and published_at is None:
            published_at = pub_h
        if upd_h:
            updated_at = upd_h

    if not title:
        title = candidate.url

    p_title, tsrc = parse_date_from_title_line(title)
    if p_title and published_at is None:
        published_at = p_title
        notes.append(f"published_from_{tsrc or 'title'}")

    access_state = result.fetch_mode
    block_reason = result.detected_block_type
    parent = metadata.get("parent_listing_url")
    detail = metadata.get("detail_url") or candidate.url

    if is_challenge_block(result.detected_block_type):
        extracted_fields["page_type"] = "challenge_or_interstitial"
        notes.append("page_type:challenge_from_block")
    elif html:
        pc = classify_html_page(
            html,
            candidate.url,
            title=title,
            block_type=result.detected_block_type,
            meta_description=summary,
        )
        extracted_fields["page_type"] = pc.page_type
        extracted_fields["page_signals"] = pc.page_signals
        notes.append(f"page_classified:{pc.page_type}")

    ing = {
        "detail_extract_success": False,
        "detail_fetch_attempt": bool(metadata.get("from_listing_expansion")),
        "metadata_fallback": True,
        "access_state": access_state,
        "block_reason": block_reason,
        "parent_listing_url": parent,
        "detail_url": detail,
        "fallback_source": "candidate_metadata_plus_response_html",
    }

    return ExtractedDocument(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        canonical_url=metadata.get("canonical_url") or candidate.url,
        title=title,
        published_at=published_at,
        updated_at=updated_at,
        author=None,
        body_text="",
        summary=summary or title,
        tags=[],
        language=None,
        outbound_links=[],
        extraction_quality_score=0.25 if summary else 0.18,
        extracted_fields=extracted_fields,
        extraction_notes=notes,
        raw_metadata={
            **metadata,
            "fetch_mode": result.fetch_mode,
            "status_code": result.status_code,
            "error": result.error,
            "ingestion": ing,
        },
    )


def metadata_only_document(candidate: CandidateURL, result: FetchResult | None = None) -> ExtractedDocument:
    if result is not None:
        return metadata_rich_document(candidate, result)
    metadata = dict(candidate.metadata or {})
    title = metadata.get("title") or candidate.url
    summary = metadata.get("snippet") or ""
    pub, src = _parse_metadata_published(metadata)
    return ExtractedDocument(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        canonical_url=candidate.url,
        title=title,
        published_at=pub,
        updated_at=None,
        author=None,
        body_text="",
        summary=summary,
        tags=[],
        language=None,
        outbound_links=[],
        extraction_quality_score=0.2,
        extracted_fields={"published_at_listing_metadata": metadata.get("published_at")} if metadata.get("published_at") else {},
        extraction_notes=["metadata_only_legacy_no_result"],
        raw_metadata={**metadata, "ingestion": {"metadata_fallback": True, "detail_fetch_attempt": False}},
    )
