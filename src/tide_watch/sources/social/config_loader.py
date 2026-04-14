"""从 YAML 加载 `social_sources`，与 official 共用文件时可并存。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tide_watch.sources.official.config_loader import default_sources_path
from tide_watch.sources.social.models import SocialRegistryConfig, SocialSourceConfig


def load_social_registry(path: str | Path | None = None) -> SocialRegistryConfig:
    cfg_path = Path(path) if path else default_sources_path()
    with cfg_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return SocialRegistryConfig(social_sources=[])
    raw_list = data.get("social_sources")
    if not isinstance(raw_list, list):
        return SocialRegistryConfig(social_sources=[])
    cleaned: list[SocialSourceConfig] = []
    for row in raw_list:
        if isinstance(row, dict):
            cleaned.append(SocialSourceConfig.model_validate(row))
    return SocialRegistryConfig(social_sources=cleaned)


def merge_social_into_yaml_dict(data: dict[str, Any], social: SocialRegistryConfig) -> dict[str, Any]:
    """测试用：把 social 配置写回 dict。"""
    out = dict(data)
    out["social_sources"] = [s.model_dump() for s in social.social_sources]
    return out
