"""Search registry helper for providers and monitors."""

from __future__ import annotations

from tide_watch.sources.search.models import SearchMonitorConfig, SearchProviderConfig, SearchRegistryConfig


class SearchRegistry:
    def __init__(self, config: SearchRegistryConfig) -> None:
        self._config = config
        self._providers = {p.provider_id: p for p in config.search_providers}
        self._monitors = {m.monitor_id: m for m in config.search_monitors}

    def iter_enabled_providers(self):
        for item in self._providers.values():
            if item.enabled:
                yield item

    def iter_enabled_monitors(self):
        for item in self._monitors.values():
            if item.enabled:
                yield item

    def provider(self, provider_id: str) -> SearchProviderConfig:
        return self._providers[provider_id]

    def monitor(self, monitor_id: str) -> SearchMonitorConfig:
        return self._monitors[monitor_id]
