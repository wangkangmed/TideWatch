from tide_watch.focused.graph import _fetch_and_classify
from tide_watch.focused.models import FetchPlan, FetchResult


def test_cloudflare_challenge_degrades_to_metadata(monkeypatch):
    def fake_run(_plan):
        return FetchResult(
            source_id="s1",
            company="c",
            url="https://x",
            status_code=403,
            headers={"server": "cloudflare", "cf-ray": "abc"},
            raw_text="Just a moment...",
            fetch_mode="direct_html",
        )

    monkeypatch.setattr("tide_watch.focused.graph.run_fetch_plan", fake_run)
    state = {
        "fetch_plans": [FetchPlan(source_id="s1", company="c", url="https://x", mode="direct_html", reason="t")]
    }
    out = _fetch_and_classify(state)
    assert out["fetch_results"][0].detected_block_type == "cloudflare_challenge"
    assert out["fetch_results"][0].fetch_mode == "metadata_only"
