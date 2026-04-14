"""默认官网 RSS 地址（可通过 TideWatchSettings 覆盖）。

说明：
- OpenAI / Google 为站点公开 RSS。
- Anthropic 站点上 ``/feeds/...`` 在部分环境会 404；默认使用社区镜像（与 feed 内 atom:self 同源内容），
  也可设置 ``TIDEWATCH_ANTHROPIC_RSS_URL`` 指向你可访问的官方 feed。
"""

# OpenAI 新闻（官网）
OPENAI_NEWS_RSS = "https://openai.com/news/rss.xml"

# Google AI / Gemini 相关（Google Blog AI 版块，公开 RSS；会 301 到 innovation-and-ai 路径）
GOOGLE_AI_BLOG_RSS = "https://blog.google/innovation-and-ai/technology/ai/rss/"

# Anthropic 新闻：官方 feed 在部分网络下不可用时的镜像（内容对应 newsroom）
ANTHROPIC_NEWS_RSS_MIRROR = (
    "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"
)

# 采集顺序：与产品名对应（OpenAI / Claude·Anthropic / Google·Gemini）
OFFICIAL_RSS_PROVIDER_ORDER: tuple[str, ...] = (
    "openai_news_rss",
    "anthropic_news_rss",
    "google_ai_blog_rss",
)
