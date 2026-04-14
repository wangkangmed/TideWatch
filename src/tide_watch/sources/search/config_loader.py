"""Load search providers/monitors from shared YAML config."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tide_watch.sources.official.config_loader import default_sources_path
from tide_watch.sources.search.models import SearchRegistryConfig


def load_search_registry(path: str | Path | None = None) -> SearchRegistryConfig:
    cfg_path = Path(path) if path else default_sources_path()
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return SearchRegistryConfig()
    payload: dict[str, Any] = {
        "search_providers": data.get("search_providers") or [],
        "search_monitors": data.get("search_monitors") or [],
    }
    return SearchRegistryConfig.model_validate(payload)
