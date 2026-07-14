from digest.models import RawItem, SeriesDef
from digest.normalize import (
    canonicalize_url,
    classify_series,
    is_relevant,
    normalize_items,
)

REGISTRY = (
    SeriesDef(
        id="f1",
        label="Formula 1",
        terms=("Formula 1", "F1", "Grand Prix", "Verstappen"),
    ),
    SeriesDef(id="indycar", label="IndyCar", terms=("IndyCar", "Indy 500", "Palou")),
    SeriesDef(id="wec", label="WEC", terms=("WEC", "Le Mans", "Hypercar", "499P")),
)


def test_canonicalize_strips_tracking_and_fragment():
    dirty = "HTTPS://www.Autosport.com/f1/news/story/?utm_source=x&fbclid=y&id=5#top"
    assert canonicalize_url(dirty) == "https://www.autosport.com/f1/news/story?id=5"


def test_canonicalize_normalizes_amp_and_trailing_slash():
    assert canonicalize_url("https://example.com/a/amp/") == "https://example.com/a"


def test_canonicalize_preserves_bare_root():
    assert canonicalize_url("https://example.com/") == "https://example.com/"
    assert canonicalize_url("https://example.com/amp/") == "https://example.com/"


def test_classify_series_prefers_source_hint():
    assert classify_series("Some ambiguous headline", "indycar", REGISTRY) == "indycar"


def test_classify_series_from_title_terms():
    assert classify_series("Verstappen wins the Grand Prix", "", REGISTRY) == "f1"
    assert classify_series("Palou dominates at Indy 500", "", REGISTRY) == "indycar"
    assert classify_series("Unrelated tech news", "", REGISTRY) == ""


def test_classify_series_first_match_wins_in_registry_order():
    # A title that could hit two series resolves to the earlier (core) one.
    assert classify_series("Verstappen tests at Le Mans", "", REGISTRY) == "f1"


def test_normalize_items_sets_domain_and_series():
    item = RawItem(
        source="rss",
        url="https://www.autosport.com/f1/?utm_source=z",
        title="Verstappen upgrade for the Grand Prix",
    )
    out = normalize_items([item], REGISTRY)[0]
    assert out.url == "https://www.autosport.com/f1"
    assert out.domain == "www.autosport.com"
    assert out.series == "f1"


def test_is_relevant_keeps_classified_story():
    assert is_relevant("Verstappen's new F1 upgrade", REGISTRY) is True


def test_is_relevant_rejects_unclassifiable_story():
    assert (
        is_relevant("Alex Palou opens a coffee shop", REGISTRY) is True
    )  # 'Palou' term
    assert is_relevant("Local council debates parking", REGISTRY) is False


def _rss(title: str, series: str = "") -> RawItem:
    return RawItem(
        source="rss", url="https://motorsport.com/x", title=title, series=series
    )


def test_normalize_drops_off_topic_series():
    # Series NOT in the registry (MotoGP, Supercars) must be dropped.
    off_topic = [
        _rss("Vinales: 'KTM sent me a contract'"),  # MotoGP
        _rss("Supercars Townsville: Waters takes win"),  # Supercars
    ]
    assert normalize_items(off_topic, REGISTRY) == []


def test_normalize_keeps_chosen_series_via_registry():
    # The leak fix, inverted: a WEC story now classifies and is KEPT (wec is followed).
    out = normalize_items([_rss("Ferrari 499P wins at Le Mans")], REGISTRY)
    assert len(out) == 1 and out[0].series == "wec"


def test_normalize_drops_bare_ambiguous_manufacturer():
    # 'Ferrari' alone, no series/event/driver term → dropped (the old leak source).
    # Note: "road-going supercar", not "hypercar" — "Hypercar" is itself a WEC
    # registry term, so that word would (correctly) classify as wec and defeat
    # the point of this test.
    assert (
        normalize_items([_rss("Ferrari unveils new road-going supercar")], REGISTRY)
        == []
    )


def test_normalize_trusts_source_series_feed():
    out = normalize_items(
        [_rss("Grosjean signs multi-year deal", series="indycar")], REGISTRY
    )
    assert len(out) == 1 and out[0].series == "indycar"
