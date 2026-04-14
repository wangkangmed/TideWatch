"""结构化索引页：changelog / release notes / docs updates 条目抽取。"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

from tide_watch.web.date_parser import parse_dates_from_html, parse_feed_date_string, parse_first_date_from_changelog_text
from tide_watch.models.ingestion import ExtractedDocument, FetchResult
from tide_watch.sources.official.source_definitions import CandidateURL

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_HREF = re.compile(
    r'href\s*=\s*(?P<q>["\'])(?P<href>[^"\']+)(?P=q)',
    re.I,
)
# HF changelog cards: markdown-ish titles in headings or list
_LI_CHUNK = re.compile(r"<li[^>]*>(.*?)</li>", re.I | re.DOTALL)


def _strip(s: str) -> str:
    t = _TAG.sub(" ", s or "")
    t = unescape(t)
    return _WS.sub(" ", t).strip()


def _is_changelogish_url(u: str) -> bool:
    p = (u or "").lower()
    return any(x in p for x in ("/changelog", "release-notes", "changelog/", "getting-started/changelog"))


def extract_changelog_like_entries(html: str, base_url: str, *, max_items: int = 40) -> list[dict[str, str]]:
    """从索引 HTML 抽 (title, detail_url, date_hint, snippet)。"""
    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    if not html:
        return entries

    # 1) 带日期的文本行（纯文本 / 去标签后）
    plain = _strip(html)
    for m in re.finditer(
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\s*[:\-–]\s*([^\n]{8,200})",
        plain,
        re.I,
    ):
        date_h = m.group(1).strip()
        title = m.group(2).strip()
        key = f"{date_h}|{title[:80]}"
        if key in seen:
            continue
        seen.add(key)
        entries.append({"title": title, "detail_url": "", "date_hint": date_h, "snippet": title[:400]})
        if len(entries) >= max_items:
            return entries

    # 2) 同域 changelog 链接 + 锚文本
    base_host = urlparse(base_url).netloc.lower()
    for m in _HREF.finditer(html):
        href = (m.group("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        if not _is_changelogish_url(href) and "/changelog" not in href.lower():
            continue
        abs_u = urljoin(base_url, href).split("#")[0]
        if urlparse(abs_u).netloc.lower() != base_host:
            continue
        if abs_u in seen:
            continue
        seen.add(abs_u)
        # 锚文本：取 <a>...</a> 内
        start = m.start()
        frag = html[start : start + 400]
        inner_m = re.search(r">([^<]{3,200})<", frag)
        title = _strip(inner_m.group(1)) if inner_m else abs_u
        entries.append({"title": title, "detail_url": abs_u, "date_hint": "", "snippet": title[:400]})
        if len(entries) >= max_items:
            return entries

    # 3) <li> 块
    if len(entries) < 3:
        for m in _LI_CHUNK.finditer(html):
            chunk = _strip(m.group(1))
            if len(chunk) < 15:
                continue
            dh = ""
            dm = re.match(
                r"^((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}|\d{4}-\d{2}-\d{2})\b",
                chunk,
                re.I,
            )
            if dm:
                dh = dm.group(1)
                chunk = chunk[len(dh) :].strip(" -:\t")
            key = chunk[:120]
            if key in seen:
                continue
            seen.add(key)
            entries.append({"title": chunk[:220], "detail_url": "", "date_hint": dh, "snippet": chunk[:400]})
            if len(entries) >= max_items:
                break

    return entries[:max_items]


def _doc_subtype(source_type: str) -> str:
    st = (source_type or "").lower()
    if "changelog" in st:
        return "changelog_entry"
    if "release" in st:
        return "release_note"
    return "docs_update"


def extract_structured_index_document(candidate: CandidateURL, result: FetchResult) -> ExtractedDocument:
    """structured_index：从索引或详情壳中抽条目，允许正文为结构化列表而非整页 HTML。"""
    metadata = dict(candidate.metadata or {})
    html = result.raw_html or result.raw_text or ""
    entries = extract_changelog_like_entries(html, candidate.url, max_items=36)
    subtype = _doc_subtype(candidate.source_type)

    lines: list[str] = []
    for e in entries:
        dh = e.get("date_hint") or ""
        du = e.get("detail_url") or ""
        t = e.get("title") or ""
        line = f"- [{dh}] {t}" + (f" :: {du}" if du else "")
        lines.append(line)

    body_text = "\n".join(lines) if lines else _strip(html)[:6000]
    summary = lines[0][:400] if lines else (metadata.get("snippet") or "")[:400]

    pub, upd, fields, notes = parse_dates_from_html(html)
    notes = list(notes)
    notes.append("structured_index_extractor")

    if not pub:
        p2, src = parse_first_date_from_changelog_text(body_text)
        if p2:
            pub = p2
            fields["changelog_text_date"] = src or "changelog_line"
            notes.append("published_from_changelog_text")

    if not pub and metadata.get("published_at"):
        pub = parse_feed_date_string(str(metadata["published_at"]))

    title = metadata.get("title")
    if not title:
        m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.DOTALL)
        if m:
            title = _strip(m.group(1))
    if not title:
        title = f"{candidate.source_id} — structured index"

    ing = {
        "detail_extract_success": bool(len(lines) >= 2 or len(body_text) > 80),
        "detail_fetch_attempt": True,
        "metadata_fallback": False,
        "structured_index": True,
        "entry_count": len(entries),
    }
    meta_out = {
        **metadata,
        "fetch_mode": result.fetch_mode,
        "status_code": result.status_code,
        "normalized_doc_type": subtype,
        "ingestion": ing,
    }
    score = 0.55 if len(entries) >= 2 else 0.38

    return ExtractedDocument(
        source_id=candidate.source_id,
        company=candidate.company,
        url=candidate.url,
        canonical_url=candidate.url,
        title=title,
        published_at=pub,
        updated_at=upd,
        author=None,
        body_text=body_text,
        summary=summary or title,
        tags=[],
        language="en",
        outbound_links=[],
        extraction_quality_score=score,
        extracted_fields={**fields, "page_type": "listing_page", "structured_entries": len(entries)},
        extraction_notes=notes,
        raw_metadata=meta_out,
    )
