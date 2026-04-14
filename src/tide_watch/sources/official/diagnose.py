"""Official source diagnostics: DNS + HTTP reachability by transport URL."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.config_loader import load_source_config
from tide_watch.sources.official.discovery.network_utils import classify_network_error, url_host_resolvable
from tide_watch.sources.official.pipeline import _apply_collection_mode, resolved_transport_strategies


def _read_resolver_sources() -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        out["resolv_conf"] = open("/etc/resolv.conf", "r", encoding="utf-8").read()
    except Exception as exc:  # noqa: BLE001
        out["resolv_conf_error"] = str(exc)
    try:
        cp = subprocess.run(
            ["resolvectl", "status"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
            check=False,
        )
        out["resolvectl_status"] = (cp.stdout or "").strip()
        if cp.returncode != 0:
            out["resolvectl_error"] = (cp.stderr or "").strip()
    except Exception as exc:  # noqa: BLE001
        out["resolvectl_error"] = str(exc)
    return out


def _socket_probe(hosts: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for h in hosts:
        row: dict[str, Any] = {"host": h, "ok": False, "addresses": [], "error": None}
        try:
            infos = socket.getaddrinfo(h, None)
            ips = []
            for it in infos:
                try:
                    ip = it[4][0]
                except Exception:  # noqa: BLE001
                    continue
                if ip and ip not in ips:
                    ips.append(ip)
            row["ok"] = True
            row["addresses"] = ips[:8]
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)
        rows.append(row)
    return rows


def _check_url(url: str, timeout: float) -> dict[str, Any]:
    out: dict[str, Any] = {"url": url, "dns_ok": url_host_resolvable(url), "http_ok": False, "status_code": None, "error": None}
    if not out["dns_ok"]:
        out["error"] = "dns_unresolvable"
        return out
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True, headers={"User-Agent": "TideWatch-Official-Diag/1.0"})
        out["status_code"] = int(r.status_code)
        out["http_ok"] = 200 <= r.status_code < 400
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{classify_network_error(exc)}:{exc}"
    return out


def run_diagnose(config_path: str | None = None) -> dict[str, Any]:
    settings = TideWatchSettings()
    cfg = load_source_config(config_path)
    by_source: dict[str, Any] = {}
    totals = Counter()
    probe_hosts: set[str] = {"openai.com", "www.anthropic.com", "deepmind.google"}
    for comp in cfg.companies:
        for src in comp.sources:
            if not src.enabled:
                continue
            strategies = _apply_collection_mode(src, resolved_transport_strategies(src), settings.official_collection_mode)
            entries = []
            for st in strategies:
                if not st.url:
                    continue
                host = urlparse(st.url).hostname
                if host:
                    probe_hosts.add(host)
                ck = _check_url(st.url, timeout=float(settings.official_http_timeout_sec))
                ck["transport"] = st.transport
                entries.append(ck)
                totals["urls"] += 1
                if ck["dns_ok"]:
                    totals["dns_ok"] += 1
                if ck["http_ok"]:
                    totals["http_ok"] += 1
                if ck["error"]:
                    totals["errors"] += 1
            by_source[src.id] = {
                "company": comp.company,
                "source_type": src.type,
                "collection_mode": settings.official_collection_mode,
                "checks": entries,
            }
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "summary": dict(totals),
        "resolver": _read_resolver_sources(),
        "socket_probe": _socket_probe(sorted(probe_hosts)),
        "by_source": by_source,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose official source DNS/HTTP reachability.")
    parser.add_argument("--config", type=str, default=None, help="Path to ai_sources.yaml (optional)")
    args = parser.parse_args()
    rep = run_diagnose(args.config)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
