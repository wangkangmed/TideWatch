from tide_watch.focused.discovery.listing_expand import extract_article_links_from_listing_html


def test_extract_links_prefers_deeper_paths():
    listing = "https://example.com/news/"
    html = """
    <html><body>
    <a href="/news/">home</a>
    <a href="/news/article-one">Article</a>
    <a href="https://other.com/x">external</a>
    <a href="/news/2024/deep-post">Deep</a>
    </body></html>
    """
    links = extract_article_links_from_listing_html(listing, html, max_links=10)
    urls = [u for u, _ in links]
    assert "https://example.com/news/article-one" in urls
    assert "https://example.com/news/2024/deep-post" in urls
    assert "https://example.com/news" not in urls
