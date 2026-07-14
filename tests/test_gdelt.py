import socket
import time
from datetime import datetime

from digest.collect.gdelt import (
    _prefer_ipv4,
    build_keyword_list,
    fetch_gdelt,
    parse_articles,
    spike_ratio,
)
from digest.models import SeriesDef

REGISTRY = (
    SeriesDef(
        id="f1",
        label="Formula 1",
        terms=("Formula 1", "F1", "Grand Prix", "Verstappen"),
    ),
    SeriesDef(id="indycar", label="IndyCar", terms=("IndyCar", "Indy 500", "Palou")),
)


def test_build_keyword_list_scopes_to_series():
    f1 = build_keyword_list(REGISTRY, "f1")
    assert "F1" in f1 and "Grand Prix" in f1
    assert "Indy 500" not in f1  # not the other series


def test_parse_articles_filters_irrelevant():
    rows = [
        {
            "url": "https://a.com/1",
            "title": "Verstappen wins the Grand Prix",
            "domain": "a.com",
        },
        {
            "url": "https://b.com/2",
            "title": "Local news about a person named Smith",
            "domain": "b.com",
        },
    ]
    items = parse_articles(rows, REGISTRY)
    assert [i.url for i in items] == ["https://a.com/1"]
    assert items[0].source == "gdelt"


def test_parse_articles_tags_series():
    rows = [
        {
            "url": "https://a.com/1",
            "title": "Verstappen wins the Grand Prix",
            "domain": "a.com",
        }
    ]
    items = parse_articles(rows, REGISTRY, series="f1")
    assert items[0].series == "f1"


class _HangingGdelt:
    """Stand-in for GdeltDoc whose network calls never return."""

    def article_search(self, *_args, **_kwargs):
        time.sleep(60)

    def timeline_search(self, *_args, **_kwargs):
        time.sleep(60)


def test_fetch_gdelt_survives_a_hanging_search():
    """A stalled GDELT connection must degrade, not hang the whole run.

    gdeltdoc issues requests.get() without a timeout, so a wedged endpoint
    would otherwise block the digest forever and it never sends the email.
    """
    since, end = datetime(2026, 7, 10), datetime(2026, 7, 11)

    articles, spikes = fetch_gdelt(REGISTRY, since, end, client=_HangingGdelt(), timeout=0.2)

    assert articles == []  # nothing collected on timeout
    assert spikes == {"f1": 1.0, "indycar": 1.0}  # spikes fall back to neutral


def test_prefer_ipv4_orders_ipv4_first(monkeypatch):
    """Inside the block, IPv4 sorts ahead of IPv6 so a black-holed IPv6 route
    (observed on the Pi deploy) never wins the connect race, while IPv6 stays
    as a fallback for hosts where IPv4 is the broken path.
    """
    v6 = (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 80, 0, 0))
    v4 = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [v6, v4])

    with _prefer_ipv4():
        families = [row[0] for row in socket.getaddrinfo("host", 80)]

    assert families == [socket.AF_INET, socket.AF_INET6]


def test_prefer_ipv4_restores_resolver(monkeypatch):
    """The patch is scoped — the original resolver returns after the block."""

    def original(*_args, **_kwargs):
        return ["sentinel"]

    monkeypatch.setattr(socket, "getaddrinfo", original)
    with _prefer_ipv4():
        pass

    assert socket.getaddrinfo is original


def test_spike_ratio_computes_last_over_mean():
    assert spike_ratio([10, 10, 10, 30]) == 3.0
    assert spike_ratio([]) == 1.0
    assert spike_ratio([5]) == 1.0
