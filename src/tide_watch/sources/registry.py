"""Provider 注册表：按 provider_id 解析 SourceConnector / Normalizer。"""

from typing import Any

from tide_watch.sources.protocols import Normalizer, SourceConnector


class SourceRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, SourceConnector] = {}
        self._normalizers: dict[str, Normalizer] = {}

    def register_connector(self, c: SourceConnector) -> None:
        self._connectors[c.provider_id] = c

    def register_normalizer(self, n: Normalizer, provider_id: str) -> None:
        self._normalizers[provider_id] = n

    def get_connector(self, provider_id: str) -> SourceConnector:
        return self._connectors[provider_id]

    def build_scope_for_provider(self, provider_id: str, base_scope: dict[str, Any]) -> dict[str, Any]:
        """可选：为某 provider 注入专用键（如 API version）。"""
        return {**base_scope, "provider_id": provider_id}
