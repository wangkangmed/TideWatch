"""注册官网 RSS connectors。"""

from tide_watch.config.settings import TideWatchSettings
from tide_watch.sources.official.defaults import OFFICIAL_RSS_PROVIDER_ORDER
from tide_watch.sources.official.rss_connector import RssOfficialConnector
from tide_watch.sources.registry import SourceRegistry


def build_official_rss_registry(settings: TideWatchSettings) -> SourceRegistry:
    reg = SourceRegistry()
    mapping: dict[str, str] = {
        "openai_news_rss": settings.openai_rss_url,
        "anthropic_news_rss": settings.anthropic_rss_url,
        "google_ai_blog_rss": settings.google_ai_rss_url,
    }
    for pid in OFFICIAL_RSS_PROVIDER_ORDER:
        url = mapping.get(pid, "").strip()
        if not url:
            continue
        reg.register_connector(
            RssOfficialConnector(
                provider_id=pid,
                feed_url=url,
                max_items=settings.max_rss_items_per_feed,
            )
        )
    return reg
