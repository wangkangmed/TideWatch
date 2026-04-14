"""兼容层：历史 ``tide_watch.focused.models`` import 转发到 canonical 模块。"""

from __future__ import annotations

from tide_watch.models.ingestion import (
    BlockType,
    ExtractedDocument,
    FetchAttempt,
    FetchPlan,
    FetchResult,
    FocusedNormalizedDocument,
    IngestionRunStats,
    SourceAccessMode,
    SourceHealth,
    SourceStrategy,
)
from tide_watch.sources.official.source_definitions import (
    CandidateSet,
    CandidateURL,
    CompanySourceConfig,
    SourceDefinition,
    SourceRegistryConfig,
)

__all__ = [
    "BlockType",
    "CandidateSet",
    "CandidateURL",
    "CompanySourceConfig",
    "ExtractedDocument",
    "FetchAttempt",
    "FetchPlan",
    "FetchResult",
    "FocusedNormalizedDocument",
    "IngestionRunStats",
    "SourceAccessMode",
    "SourceDefinition",
    "SourceHealth",
    "SourceRegistryConfig",
    "SourceStrategy",
]
