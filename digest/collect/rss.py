import calendar
from datetime import UTC, datetime

import feedparser

from digest.models import RawItem


def _entry_datetime(entry) -> datetime | None:
    struct = getattr(entry, "published_parsed", None)
    if not struct:
        return None
    return datetime.fromtimestamp(calendar.timegm(struct), tz=UTC)


def parse_feed(parsed, feed_series: str, since: datetime) -> list[RawItem]:
    """Convert a feedparser result into RawItems within the window."""
    items = []
    for entry in parsed.entries:
        published = _entry_datetime(entry)
        if published is not None and published < since:
            continue
        items.append(RawItem(
            source="rss",
            url=getattr(entry, "link", ""),
            title=getattr(entry, "title", ""),
            published_at=published,
            series=feed_series,
        ))
    return items


def fetch_rss(feeds: list[dict], since: datetime) -> list[RawItem]:
    """Fetch and parse each configured RSS feed. Failures per feed are skipped."""
    items = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            items.extend(parse_feed(parsed, feed.get("series", ""), since))
        except Exception as exc:                    # noqa: BLE001 — one bad feed must not kill the run
            print(f"[rss] failed {feed.get('url')}: {exc}")
    return items
