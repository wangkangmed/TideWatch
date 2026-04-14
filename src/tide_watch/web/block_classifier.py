"""Fetch result and anti-bot classifier (detection only, no bypass)."""

from __future__ import annotations

from tide_watch.models.ingestion import BlockType, FetchResult

_CHALLENGE_PATTERNS = (
    "just a moment",
    "attention required",
    "checking your browser",
    "cf-chl",
    "challenge-platform",
    "challenge",
)


def classify_fetch_result(result: FetchResult) -> FetchResult:
    status = result.status_code
    headers = {k.lower(): v for k, v in (result.headers or {}).items()}
    body = (result.raw_text or result.raw_html or "").lower()

    if status is None:
        result.detected_block_type = "network_error"
        result.retryable = True
        result.success = False
        return result

    if status in (301, 302):
        result.detected_block_type = "redirect"
        result.success = True
        result.retryable = False
        return result

    if status == 429:
        result.detected_block_type = "rate_limited"
        result.success = False
        result.retryable = True
        return result

    if status == 403:
        if "cf-ray" in headers or "cloudflare" in str(headers.get("server", "")).lower():
            result.detected_platform = "cloudflare"
            if any(p in body for p in _CHALLENGE_PATTERNS):
                result.detected_block_type = "cloudflare_challenge"
                result.retryable = False
                result.success = False
                return result
            result.detected_block_type = "cloudflare_block"
            result.retryable = False
            result.success = False
            return result
        if body:
            result.detected_block_type = "origin_forbidden"
        else:
            result.detected_block_type = "unknown_403"
        result.retryable = result.detected_block_type == "unknown_403"
        result.success = False
        return result

    if status >= 400:
        result.detected_block_type = "network_error"
        result.success = False
        result.retryable = status >= 500
        return result

    ctype = (result.content_type or "").lower()
    blob = (result.raw_text or result.raw_html or "") or ""
    blob_l = blob.lstrip()
    head = blob_l[:12000].lower()
    looks_like_html = blob_l.startswith("<!DOCTYPE") or blob_l.startswith("<html") or "<article" in head
    looks_like_heavy_markup = blob_l.count("<a ") > 12 and len(blob_l) > 2500 and "<div" in head

    if ctype and "html" not in ctype and "xml" not in ctype:
        if "json" in ctype and ("<div" in head or "<span" in head):
            # 部分站点以 application/json 返回含 HTML 片段的 RSC 负载
            pass
        elif looks_like_html or looks_like_heavy_markup:
            # 错误 MIME 但实际为 HTML，允许进入抽取管线
            pass
        elif "json" in ctype or "text" in ctype:
            pass
        else:
            result.detected_block_type = "unsupported_content_type"
            result.success = False
            result.retryable = False
            return result

    result.detected_block_type = "success"
    result.success = True
    result.retryable = False
    return result


def is_challenge_block(block_type: BlockType) -> bool:
    return block_type in ("cloudflare_challenge", "cloudflare_block")
