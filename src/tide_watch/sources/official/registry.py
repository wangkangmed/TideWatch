"""Registry helper for source definitions."""

from __future__ import annotations

from tide_watch.sources.official.source_definitions import SourceDefinition, SourceRegistryConfig


class SourceRegistry:
    def __init__(self, config: SourceRegistryConfig) -> None:
        self._config = config
        self._sources: dict[str, tuple[str, SourceDefinition]] = {}
        for company in config.companies:
            for src in company.sources:
                self._sources[src.id] = (company.company, src)

    def get(self, source_id: str) -> tuple[str, SourceDefinition]:
        return self._sources[source_id]

    def iter_sources(self):
        for source_id, val in self._sources.items():
            company, source = val
            yield source_id, company, source
