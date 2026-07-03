from datetime import UTC, datetime
from types import SimpleNamespace

from digest.collect.rss import fetch_rss, parse_feed


def _entry(title, link, published_struct):
    return SimpleNamespace(title=title, link=link, published_parsed=published_struct)


def test_parse_feed_keeps_recent_entries():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    recent = _entry("Verstappen wins", "https://autosport.com/a",
                    (2026, 7, 3, 8, 0, 0, 0, 0, 0))
    parsed = SimpleNamespace(entries=[recent])

    items = parse_feed(parsed, "f1", since)

    assert len(items) == 1
    assert items[0].source == "rss"
    assert items[0].title == "Verstappen wins"
    assert items[0].url == "https://autosport.com/a"
    assert items[0].series == "f1"


def test_parse_feed_drops_old_entries():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    old = _entry("Ancient news", "https://autosport.com/b",
                 (2026, 6, 1, 8, 0, 0, 0, 0, 0))
    parsed = SimpleNamespace(entries=[old])

    assert parse_feed(parsed, "f1", since) == []


def test_parse_feed_keeps_entry_with_no_date():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    dateless = SimpleNamespace(title="No date", link="https://x/c", published_parsed=None)
    parsed = SimpleNamespace(entries=[dateless])

    items = parse_feed(parsed, "", since)
    assert len(items) == 1        # keep when we can't tell; downstream window filters


def test_fetch_rss_isolates_a_failing_feed(monkeypatch):
    good_entry = _entry("Recent story", "https://good.com/x",
                        (2026, 7, 3, 8, 0, 0, 0, 0, 0))

    def fake_parse(url):
        if "bad" in url:
            raise ValueError("boom")
        return SimpleNamespace(entries=[good_entry])

    monkeypatch.setattr("digest.collect.rss.feedparser.parse", fake_parse)
    feeds = [{"url": "https://bad.com/feed", "series": "f1"},
             {"url": "https://good.com/feed", "series": "indycar"}]

    items = fetch_rss(feeds, datetime(2026, 7, 2, tzinfo=UTC))

    assert len(items) == 1                      # bad feed skipped, good feed collected
    assert items[0].url == "https://good.com/x"
    assert items[0].series == "indycar"
