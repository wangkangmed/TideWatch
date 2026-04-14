from tide_watch.focused.fetchers import run_fetch_plan
from tide_watch.focused.models import FetchPlan


def test_429_backoff_retries(monkeypatch):
    attempts = {"n": 0}
    sleeps: list[float] = []

    class Resp:
        def __init__(self, code):
            self.status_code = code
            self.url = "https://x"
            self.headers = {"content-type": "text/html"}
            self.text = "ok"

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def get(self, _url):
            attempts["n"] += 1
            if attempts["n"] < 3:
                return Resp(429)
            return Resp(200)

    monkeypatch.setattr("tide_watch.web.http_client.httpx.Client", Client)
    plan = FetchPlan(source_id="s", company="c", url="https://x", mode="direct_html", reason="t")
    result = run_fetch_plan(plan, sleep_fn=lambda x: sleeps.append(x), max_retries_429=3)
    assert result.status_code == 200
    assert attempts["n"] == 3
    assert sleeps == [1, 2]
