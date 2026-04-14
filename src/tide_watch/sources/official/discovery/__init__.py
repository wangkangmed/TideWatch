"""Official discovery transports（RSS / Sitemap / HTML listing / REST）。"""

from tide_watch.sources.official.discovery.api import discover_from_rest_api
from tide_watch.sources.official.discovery.html_listing import discover_from_listing
from tide_watch.sources.official.discovery.rss import discover_from_rss
from tide_watch.sources.official.discovery.sitemap import discover_from_sitemap

__all__ = [
    "discover_from_listing",
    "discover_from_rest_api",
    "discover_from_rss",
    "discover_from_sitemap",
]
