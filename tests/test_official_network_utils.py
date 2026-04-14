from __future__ import annotations

import httpx

from tide_watch.sources.official.discovery.network_utils import classify_network_error


def test_classify_network_error_dns():
    err = httpx.ConnectError("[Errno -2] Name or service not known")
    assert classify_network_error(err) == "dns"


def test_classify_network_error_timeout():
    err = httpx.ReadTimeout("timed out")
    assert classify_network_error(err) == "timeout"
