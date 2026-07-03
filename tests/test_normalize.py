from digest.models import RawItem
from digest.normalize import canonicalize_url, classify_series, normalize_items

KEYWORDS = {
    "series_f1": ["Formula 1", "F1", "Grand Prix"],
    "series_indycar": ["IndyCar", "Indy 500"],
    "teams": ["Ferrari", "Penske"],
    "drivers": ["Verstappen", "Palou"],
}


def test_canonicalize_strips_tracking_and_fragment():
    dirty = "HTTPS://www.Autosport.com/f1/news/story/?utm_source=x&fbclid=y&id=5#top"
    assert canonicalize_url(dirty) == "https://www.autosport.com/f1/news/story?id=5"


def test_canonicalize_normalizes_amp_and_trailing_slash():
    assert canonicalize_url("https://example.com/a/amp/") == "https://example.com/a"


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
