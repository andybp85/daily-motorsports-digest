from digest.models import RawItem
from digest.normalize import canonicalize_url, classify_series, is_relevant, normalize_items

KEYWORDS = {
    "series_f1": ["Formula 1", "F1", "Grand Prix"],
    "series_indycar": ["IndyCar", "Indy 500"],
    "teams": ["Ferrari", "Penske"],
    "drivers": ["Verstappen", "Palou"],
    "anchors": ["F1", "IndyCar", "racing", "Grand Prix", "qualifying"],
}


def test_canonicalize_strips_tracking_and_fragment():
    dirty = "HTTPS://www.Autosport.com/f1/news/story/?utm_source=x&fbclid=y&id=5#top"
    assert canonicalize_url(dirty) == "https://www.autosport.com/f1/news/story?id=5"


def test_canonicalize_normalizes_amp_and_trailing_slash():
    assert canonicalize_url("https://example.com/a/amp/") == "https://example.com/a"


def test_canonicalize_preserves_bare_root():
    assert canonicalize_url("https://example.com/") == "https://example.com/"
    assert canonicalize_url("https://example.com/amp/") == "https://example.com/"


def test_classify_series_prefers_source_hint():
    assert classify_series("Some ambiguous headline", "indycar", KEYWORDS) == "indycar"


def test_classify_series_from_title_keywords():
    assert classify_series("Verstappen wins the Grand Prix", "", KEYWORDS) == "f1"
    assert classify_series("Palou dominates at Indy 500", "", KEYWORDS) == "indycar"
    assert classify_series("Unrelated tech news", "", KEYWORDS) == ""


def test_normalize_items_sets_domain_and_series():
    item = RawItem(source="rss", url="https://www.autosport.com/f1/?utm_source=z",
                   title="Ferrari upgrade for the Grand Prix")
    out = normalize_items([item], KEYWORDS)[0]
    assert out.url == "https://www.autosport.com/f1"
    assert out.domain == "www.autosport.com"
    assert out.series == "f1"


def test_is_relevant_accepts_series_term():
    assert is_relevant("Ferrari's new F1 upgrade", KEYWORDS) is True


def test_is_relevant_requires_anchor_for_bare_driver_name():
    # "Palou" alone with no motorsport anchor → reject
    assert is_relevant("Alex Palou opens a coffee shop", KEYWORDS) is False
    # "Palou" WITH an anchor term → accept
    assert is_relevant("Palou fastest in IndyCar qualifying", KEYWORDS) is True


def _rss(title: str, series: str = "") -> RawItem:
    return RawItem(source="rss", url="https://motorsport.com/x", title=title, series=series)


def test_normalize_drops_off_topic_series():
    # General-feed (series="") stories from other series must be dropped.
    off_topic = [
        _rss("Vinales: 'KTM sent me a contract'"),          # MotoGP
        _rss("Supercars Townsville: Waters takes win"),      # Supercars
        _rss("Monaco date change could save Formula E career"),  # Formula E
    ]
    assert normalize_items(off_topic, KEYWORDS) == []


def test_normalize_keeps_relevant_without_series_term():
    # A team story with no series term still passes via is_relevant, series stays "".
    out = normalize_items([_rss("Is Red Bull better off after Horner's exit?")],
                          {**KEYWORDS, "teams": ["Red Bull"]})
    assert len(out) == 1 and out[0].series == ""


def test_normalize_trusts_source_series_feed():
    # An IndyCar-tagged feed item is kept even if its title lacks a keyword.
    out = normalize_items([_rss("Grosjean signs multi-year deal", series="indycar")], KEYWORDS)
    assert len(out) == 1 and out[0].series == "indycar"
