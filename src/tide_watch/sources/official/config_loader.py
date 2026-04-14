"""Load source configuration for focused ingestion."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tide_watch.sources.official.source_definitions import SourceRegistryConfig


def default_sources_path() -> Path:
    # official -> sources -> tide_watch -> src -> 仓库根 TideWatch
    return Path(__file__).resolve().parents[4] / "configs" / "sources" / "ai_sources.yaml"


def _ensure_source_url(item: dict[str, Any]) -> None:
    if item.get("url"):
        return
    for s in item.get("strategies") or []:
        if not isinstance(s, dict):
            continue
        if s.get("transport") == "html_listing" and s.get("url"):
            item["url"] = s["url"]
            return
    for s in item.get("strategies") or []:
        if isinstance(s, dict) and s.get("url"):
            item["url"] = s["url"]
            return
    item.setdefault("url", "about:blank")


def _normalize_registry_dict(data: dict[str, Any]) -> dict[str, Any]:
    if "companies" in data:
        return data
    osrc = data.get("official_sources")
    if not isinstance(osrc, list):
        return data
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for item in osrc:
        if not isinstance(item, dict):
            continue
        prov = str(item.get("provider") or "unknown")
        row = dict(item)
        if "source_id" in row and "id" not in row:
            row["id"] = row.pop("source_id")
        row.pop("provider", None)
        by_provider.setdefault(prov, []).append(row)
    return {"companies": [{"company": name, "tags": [], "sources": srcs} for name, srcs in by_provider.items()]}


def load_source_config(path: str | None = None) -> SourceRegistryConfig:
    cfg_path = Path(path) if path else default_sources_path()
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    data = _normalize_registry_dict(data if isinstance(data, dict) else {})
    for comp in data.get("companies") or []:
        if not isinstance(comp, dict):
            continue
        for src in comp.get("sources") or []:
            if isinstance(src, dict):
                _ensure_source_url(src)
    return SourceRegistryConfig.model_validate(data)
