from tide_watch.focused.classifier import classify_fetch_result
from tide_watch.focused.models import FetchResult


def _base_result(**kwargs):
    return FetchResult(source_id="s", company="c", url="https://x", fetch_mode="direct_html", **kwargs)


def test_cloudflare_challenge_classified():
    r = _base_result(
        status_code=403,
        headers={"server": "cloudflare", "cf-ray": "abc"},
        raw_text="<title>Just a moment...</title>",
    )
    out = classify_fetch_result(r)
    assert out.detected_block_type == "cloudflare_challenge"
    assert out.retryable is False


def test_origin_403_classified():
    r = _base_result(status_code=403, headers={"server": "nginx"}, raw_text="Forbidden")
    out = classify_fetch_result(r)
    assert out.detected_block_type in {"origin_forbidden", "unknown_403"}


def test_rate_limited_classified():
    r = _base_result(status_code=429, headers={}, raw_text="")
    out = classify_fetch_result(r)
    assert out.detected_block_type == "rate_limited"
    assert out.retryable is True
