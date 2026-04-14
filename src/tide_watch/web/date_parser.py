"""Parse published / updated timestamps from HTML, JSON-LD, and feed strings."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

# meta / link
_META_ARTICLE_PUB = re.compile(
    r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_OG_PUB = re.compile(
    r'<meta[^>]+property=["\']og:published_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_PUBDATE = re.compile(
    r'<meta[^>]+name=["\']pubdate["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_ARTICLE_MOD = re.compile(
    r'<meta[^>]+property=["\']article:modified_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_OG_UPDATED = re.compile(
    r'<meta[^>]+property=["\']og:updated_time["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_META_NAME_LASTMOD = re.compile(
    r'<meta[^>]+name=["\']lastmod["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)

_TIME_DT = re.compile(
    r'<time[^>]+datetime=["\']([^"\']+)["\']',
    re.I,
)
_TITLE_DATE_SHORT = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}\b",
    re.I,
)
# changelog 行: "April 4, 2026" 或 "2026-04-04" 起行
_CHANGELOG_LINE = re.compile(
    r"^\s*((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}"
    r"|\d{4}-\d{2}-\d{2})\s*[:\-–]?\s*(.+)$",
    re.I | re.MULTILINE,
)
_SCRIPT_JSONLD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.DOTALL,
)

_WS = re.compile(r"\s+")


def _strip_tags(s: str) -> str:
    return _WS.sub(" ", re.sub(r"<[^>]+>", " ", unescape(s or ""))).strip()


def _parse_iso_like(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    # Zulu
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_rfc3339_or_iso(raw: str) -> datetime | None:
    """Accept W3C / ISO 8601 style strings."""
    return _parse_iso_like(raw)


def parse_feed_date_string(raw: str | None) -> datetime | None:
    """RSS pubDate / Atom published / updated (RFC 2822 or ISO)."""
    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    iso = _parse_iso_like(s)
    if iso:
        return iso
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def _walk_jsonld(obj: Any, out: dict[str, list[str]]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in ("datepublished", "datecreated", "uploaddate"):
                if isinstance(v, str):
                    out.setdefault("published", []).append(v)
                elif isinstance(v, list):
                    for x in v:
                        if isinstance(x, str):
                            out.setdefault("published", []).append(x)
            elif lk in ("datemodified", "dateupdated"):
                if isinstance(v, str):
                    out.setdefault("modified", []).append(v)
            elif lk == "@graph":
                if isinstance(v, list):
                    for item in v:
                        _walk_jsonld(item, out)
            else:
                _walk_jsonld(v, out)
    elif isinstance(obj, list):
        for item in obj:
            _walk_jsonld(item, out)


def _parse_jsonld_dates(html: str) -> tuple[datetime | None, datetime | None, dict[str, Any]]:
    fields: dict[str, Any] = {}
    pub_raw: list[str] = []
    mod_raw: list[str] = []
    for m in _SCRIPT_JSONLD.finditer(html or ""):
        blob = _strip_tags(m.group(1))
        if not blob:
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        bucket: dict[str, list[str]] = {}
        _walk_jsonld(data, bucket)
        pub_raw.extend(bucket.get("published") or [])
        mod_raw.extend(bucket.get("modified") or [])
    published: datetime | None = None
    updated: datetime | None = None
    for raw in pub_raw:
        dt = _parse_iso_like(raw)
        if dt:
            published = dt
            fields["json_ld_datePublished"] = raw
            break
    for raw in mod_raw:
        dt = _parse_iso_like(raw)
        if dt:
            updated = dt
            fields["json_ld_dateModified"] = raw
            break
    return published, updated, fields


def parse_dates_from_html(html: str) -> tuple[datetime | None, datetime | None, dict[str, Any], list[str]]:
    """
    Returns (published_at, updated_at, extracted_fields, extraction_notes).
    Prefer article:published_time / og:published_time / JSON-LD datePublished for published_at.
    """
    notes: list[str] = []
    fields: dict[str, Any] = {}
    published: datetime | None = None
    updated: datetime | None = None
    h = html or ""

    for label, pattern in (
        ("article:published_time", _META_ARTICLE_PUB),
        ("og:published_time", _META_OG_PUB),
        ("pubdate", _META_PUBDATE),
    ):
        m = pattern.search(h)
        if m:
            raw = m.group(1).strip()
            dt = _parse_iso_like(raw)
            if dt:
                published = dt
                fields[label] = raw
                notes.append(f"published_from_meta:{label}")
                break

    if published is None:
        jp, ju, jf = _parse_jsonld_dates(h)
        if jp:
            published = jp
            notes.append("published_from_json_ld")
        if ju:
            updated = ju
        fields.update(jf)

    if published is None:
        # 收集所有 <time datetime>，取第一个可解析的
        for m in _TIME_DT.finditer(h):
            raw = m.group(1).strip()
            dt = _parse_iso_like(raw)
            if dt:
                published = dt
                fields["time_datetime"] = raw
                notes.append("published_from_time_tag")
                break

    m = _META_ARTICLE_MOD.search(h)
    if m:
        raw = m.group(1).strip()
        dt = _parse_iso_like(raw)
        if dt:
            updated = updated or dt
            fields["article:modified_time"] = raw
            notes.append("updated_from_meta:article:modified_time")
    m = _META_OG_UPDATED.search(h)
    if m:
        raw = m.group(1).strip()
        dt = _parse_iso_like(raw)
        if dt and updated is None:
            updated = dt
            fields["og:updated_time"] = raw
            notes.append("updated_from_meta:og:updated_time")

    # Weak lastmod only if nothing else (do not pretend it is true publish time; note only)
    if published is None:
        m = _META_NAME_LASTMOD.search(h)
        if m:
            raw = m.group(1).strip()
            dt = _parse_iso_like(raw)
            if dt:
                published = dt
                fields["lastmod_name_meta_weak"] = raw
                notes.append("published_weak_fallback_name_lastmod")

    return published, updated, fields, notes


_MONTH_MAP = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def parse_date_from_title_line(title: str | None) -> tuple[datetime | None, str | None]:
    """从标题行解析 'Mon DD, YYYY'（常见于 Anthropic 列表标题）。"""
    if not title:
        return None, None
    m = _TITLE_DATE_SHORT.search(title)
    if not m:
        return None, None
    raw = m.group(0).strip()
    try:
        dt = parsedate_to_datetime(raw + " 12:00:00 UTC")
    except (TypeError, ValueError, OverflowError):
        try:
            parts = raw.replace(",", "").split()
            mon = _MONTH_MAP.get(parts[0][:3].lower())
            if not mon:
                return None, None
            day = int(parts[1])
            year = int(parts[2])
            dt = datetime(year, mon, day, 12, 0, 0, tzinfo=timezone.utc)
        except (IndexError, ValueError):
            return None, None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc), "title_month_day_year"


def parse_first_date_from_changelog_text(text: str) -> tuple[datetime | None, str | None]:
    """从 changelog 纯文本/去标签 HTML 中取第一条日期行。"""
    if not text:
        return None, None
    for line in text.splitlines()[:80]:
        m = _CHANGELOG_LINE.match(line.strip())
        if not m:
            continue
        raw_date = m.group(1).strip()
        dt = _parse_iso_like(raw_date)
        if dt:
            return dt, "changelog_iso_line"
        for fmt in ("%B %d, %Y", "%b %d, %Y"):
            try:
                dtp = datetime.strptime(raw_date.replace(",", "").strip(), fmt.replace(",", "").strip())
                dtp = dtp.replace(tzinfo=timezone.utc)
                return dtp, "changelog_verbal_line"
            except ValueError:
                continue
        try:
            dtp = parsedate_to_datetime(raw_date)
            if dtp.tzinfo is None:
                dtp = dtp.replace(tzinfo=timezone.utc)
            return dtp.astimezone(timezone.utc), "changelog_verbal_line"
        except (TypeError, ValueError, OverflowError):
            continue
    return None, None
