"""页面类型判定单元测试。"""

from tide_watch.focused.page_classifier import classify_html_page


def test_article_page_from_json_ld_newsarticle():
    html = """
    <html><head>
    <script type="application/ld+json">{"@type":"NewsArticle","headline":"Hi","datePublished":"2026-01-15T10:00:00Z"}</script>
    </head><body><article><p>Long body text here. """ + ("word " * 200) + """</p></article></body></html>
    """
    c = classify_html_page(html, "https://example.com/news/some-post", title="Post", block_type="success")
    assert c.page_type == "article_page"
    assert c.body_handling == "full"


def test_aggregation_from_url_path():
    html = "<html><body>" + ("<a href=/x>l</a>" * 5) + "<p>short</p></body></html>"
    c = classify_html_page(
        html,
        "https://www.microsoft.com/en-us/ai/blog/content-type/events",
        title="Events",
        block_type="success",
    )
    assert c.page_type == "aggregation_page"


def test_challenge_interstitial():
    html = "<html><body>Just a moment... checking your browser</body></html>"
    c = classify_html_page(html, "https://openai.com/news", title="https://openai.com/news", block_type="cloudflare_challenge")
    assert c.page_type == "challenge_or_interstitial"


def test_long_text_but_listing_high_link_density():
    body = "<div>" + ("<a href='/p'>card</a><div class='card'>x</div>" * 25) + "</div>"
    html = f"<html><body>{body}<p>{'text ' * 400}</p></body></html>"
    c = classify_html_page(html, "https://example.com/blog", title="Blog", block_type="success")
    assert c.page_type in ("aggregation_page", "listing_page")
