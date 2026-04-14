"""兼容层：列表展开 + legacy 链接抽取。"""

from tide_watch.sources.official.discovery.listing_expand_legacy import (  # noqa: F401
    extract_article_links_from_listing_html,
)
from tide_watch.sources.official.enrichment.listing_expand import expand_listing_seed  # noqa: F401
