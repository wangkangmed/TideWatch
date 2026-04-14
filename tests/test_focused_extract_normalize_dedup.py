from datetime import datetime, timezone

from tide_watch.focused.deduper import dedup_documents
from tide_watch.focused.extractors import metadata_only_document
from tide_watch.focused.models import CandidateURL, FetchResult
from tide_watch.focused.normalizers import normalize_document


def test_metadata_only_generates_normalized_doc():
    cand = CandidateURL(
        source_id="s1",
        company="OpenAI",
        url="https://example.com/news",
        discovered_at=datetime.now(timezone.utc),
        source_type="newsroom",
        metadata={"title": "hello", "snippet": "world"},
    )
    ex = metadata_only_document(cand)
    result = FetchResult(source_id="s1", company="OpenAI", url=cand.url, fetch_mode="metadata_only", status_code=200)
    norm = normalize_document(ex, result, source_type=cand.source_type, doc_type_hint="listing")
    assert norm.document_id
    assert norm.content_hash
    assert norm.title == "hello"


def test_dedup_works_on_canonical_and_hash():
    cand = CandidateURL(
        source_id="s1",
        company="OpenAI",
        url="https://example.com/news?a=1&utm_source=x",
        discovered_at=datetime.now(timezone.utc),
        source_type="newsroom",
        metadata={"title": "A"},
    )
    ex = metadata_only_document(cand)
    result = FetchResult(source_id="s1", company="OpenAI", url=cand.url, fetch_mode="metadata_only", status_code=200)
    n1 = normalize_document(ex, result, source_type="newsroom", doc_type_hint="listing")
    n2 = normalize_document(ex, result, source_type="newsroom", doc_type_hint="listing")
    out = dedup_documents([n1, n2])
    assert len(out) == 1
