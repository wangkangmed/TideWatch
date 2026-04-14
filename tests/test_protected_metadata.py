from datetime import datetime, timezone

from tide_watch.focused.extractors import metadata_rich_document
from tide_watch.focused.models import CandidateURL, FetchResult


def test_metadata_rich_uses_display_name_when_url_is_title():
    cand = CandidateURL(
        source_id="openai_news",
        company="OpenAI",
        url="https://openai.com/news",
        discovered_at=datetime.now(timezone.utc),
        source_type="newsroom",
        metadata={
            "display_name": "OpenAI Newsroom",
            "title": "https://openai.com/news",
            "snippet": "",
            "source_strategy": "protected",
        },
    )
    html = '<html><head><title>Just a moment...</title><meta property="og:description" content="Security check"></head><body>cf-challenge</body></html>'
    result = FetchResult(
        source_id="openai_news",
        company="OpenAI",
        url=cand.url,
        fetch_mode="metadata_only",
        status_code=403,
        success=False,
        raw_html=html,
        raw_text=html,
        detected_block_type="cloudflare_challenge",
    )
    doc = metadata_rich_document(cand, result)
    assert doc.title == "OpenAI Newsroom"
    assert "Security" in (doc.summary or "") or doc.summary


def test_fallback_title_for_known_protected_id():
    cand = CandidateURL(
        source_id="xai_news",
        company="xAI",
        url="https://x.ai/news",
        discovered_at=datetime.now(timezone.utc),
        source_type="newsroom",
        metadata={"title": "https://x.ai/news", "snippet": ""},
    )
    result = FetchResult(
        source_id="xai_news",
        company="xAI",
        url=cand.url,
        fetch_mode="metadata_only",
        status_code=403,
        success=False,
        detected_block_type="cloudflare_challenge",
    )
    doc = metadata_rich_document(cand, result)
    assert doc.title == "xAI News"
