from labs.projects.intel_news_scraper.scraper import parse_news_items


def test_parse_news_items_filters_and_deduplicates() -> None:
    html = """
    <html><body>
      <a href="/news/first-update">First major update released for players</a>
      <a href="/news/first-update">First major update released for players</a>
      <a href="/news/second-update">Second news coverage with details</a>
      <a href="/forum/thread">Community thread without keyword</a>
      <a href="javascript:void(0)">Broken link for news</a>
    </body></html>
    """

    items = parse_news_items(html=html, source_url="https://tibiantis.online/news", max_items=10)

    assert len(items) == 2
    assert items[0]["url"] == "https://tibiantis.online/news/first-update"
    assert items[0]["title"] == "First major update released for players"
    assert items[1]["url"] == "https://tibiantis.online/news/second-update"


def test_parse_news_items_extracts_latestnews_comment_entries() -> None:
    html = """
    <div>
      <small>Kay, 04 Apr 2026 19:41:55 CEST <a href='/?page=viewtopic&id=655' class='menulink_hs'>Comment (0)</a></small>
      <small>Kay, 31 Jan 2026 10:11:32 CET <a href='/?page=viewtopic&id=633' class='menulink_hs'>Comment (0)</a></small>
    </div>
    """

    items = parse_news_items(html=html, source_url="https://tibiantis.online/index.php?subtopic=latestnews", max_items=10)

    assert len(items) == 2
    assert items[0]["url"].endswith("?page=viewtopic&id=655")
    assert "News update (Kay, 04 Apr 2026" in items[0]["title"]
    assert items[1]["url"].endswith("?page=viewtopic&id=633")
