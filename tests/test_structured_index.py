from datetime import datetime, timezone

from tide_watch.focused.models import CandidateURL, FetchResult
from tide_watch.focused.structured_index import extract_changelog_like_entries, extract_structured_index_document


def test_changelog_index_extracts_multiple_entries():
    html = """
    <html><body>
    <a href="/changelog/item-one">Retirement of Embed v2</a>
    <a href="/changelog/item-two">Announcing Transcribe</a>
    <p>April 4, 2026: Model deprecation notice</p>
    </body></html>
    """
    entries = extract_changelog_like_entries(html, "https://docs.example.com/changelog", max_items=20)
    assert len(entries) >= 2
    urls = [e.get("detail_url", "") for e in entries]
    assert any("item-one" in u for u in urls)


def test_structured_index_document_without_detail_fetch():
    cand = CandidateURL(
        source_id="hf_changelog",
        company="HF",
        url="https://huggingface.co/changelog",
        discovered_at=datetime.now(timezone.utc),
        source_type="changelog",
        metadata={"source_strategy": "structured_index", "seed": True},
    )
    html = "<html><title>Changelog</title><body><li>2026-01-01 — ZeroGPU overquota</li></body></html>"
    result = FetchResult(
        source_id=cand.source_id,
        company=cand.company,
        url=cand.url,
        fetch_mode="listing_only",
        status_code=200,
        success=True,
        raw_html=html,
        raw_text=html,
    )
    doc = extract_structured_index_document(cand, result)
    assert doc.body_text
    assert "ingestion" in doc.raw_metadata
    assert doc.raw_metadata.get("normalized_doc_type") == "changelog_entry"
