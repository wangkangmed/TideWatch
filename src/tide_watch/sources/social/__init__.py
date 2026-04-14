"""社媒统一 pipeline：配置、connector、discover/enrich、RawFetchBatch 输出。"""

from tide_watch.sources.social.config_loader import load_social_registry
from tide_watch.sources.social.models import SocialCandidateItem, SocialRegistryConfig, SocialSourceConfig
from tide_watch.sources.social.pipeline import collect_social_batches
from tide_watch.sources.social.registry import get_connector_for_source

__all__ = [
    "SocialSourceConfig",
    "SocialCandidateItem",
    "SocialRegistryConfig",
    "load_social_registry",
    "get_connector_for_source",
    "collect_social_batches",
]
