from tide_watch.focused.date_parser import (
    parse_date_from_title_line,
    parse_dates_from_html,
    parse_feed_date_string,
    parse_first_date_from_changelog_text,
)


def test_json_ld_datepublished():
    html = """<script type="application/ld+json">
    {"@type":"NewsArticle","datePublished":"2025-06-01T08:00:00+00:00"}
    </script>"""
    pub, upd, fields, notes = parse_dates_from_html(html)
    assert pub is not None
    assert pub.year == 2025
    assert "json_ld" in " ".join(notes).lower() or "published" in " ".join(notes).lower()


def test_meta_article_published_time():
    html = '<meta property="article:published_time" content="2024-03-20T12:00:00Z">'
    pub, _, _, notes = parse_dates_from_html(html)
    assert pub is not None
    assert any("article:published" in n for n in notes)


def test_time_datetime_tag():
    html = '<time datetime="2023-11-05">Nov 5</time>'
    pub, _, _, _ = parse_dates_from_html(html)
    assert pub is not None


def test_changelog_text_date_line():
    text = "March 26, 2026: Announcing the Cohere Transcribe model\nMore text"
    pub, src = parse_first_date_from_changelog_text(text)
    assert pub is not None
    assert src


def test_rss_pubdate_string():
    dt = parse_feed_date_string("Mon, 02 Jan 2026 15:30:00 GMT")
    assert dt is not None


def test_title_month_day_year():
    title = "Product Feb 17, 2026 Introducing Claude Sonnet"
    pub, src = parse_date_from_title_line(title)
    assert pub is not None
    assert pub.month == 2 and pub.day == 17
    assert src
