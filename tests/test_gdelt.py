from digest.collect.gdelt import (build_keyword_list, is_relevant, parse_articles, spike_ratio)

KEYWORDS = {
    "series_f1": ["Formula 1", "F1", "Grand Prix"],
    "series_indycar": ["IndyCar", "Indy 500"],
    "teams": ["Ferrari", "Penske"],
    "drivers": ["Verstappen", "Russell", "Palou"],
    "anchors": ["F1", "IndyCar", "racing", "Grand Prix"],
}


def test_build_keyword_list_scopes_to_series():
    f1 = build_keyword_list(KEYWORDS, "f1")
    assert set(f1) == {"Formula 1", "F1", "Grand Prix"}     # series terms only
    assert "Indy 500" not in f1                             # not the other series
    # teams/drivers are NOT in the API query — they'd overflow GDELT's length
    # limit; is_relevant() applies them downstream instead.
    assert "Ferrari" not in f1 and "Verstappen" not in f1


def test_is_relevant_accepts_series_term():
    assert is_relevant("Ferrari's new F1 upgrade", KEYWORDS) is True


def test_is_relevant_requires_anchor_for_bare_driver_name():
    # "Russell" alone (a common surname) with no motorsport anchor → reject
    assert is_relevant("Senator Russell speaks on policy", KEYWORDS) is False
    # "Russell" WITH an anchor term → accept
    assert is_relevant("Russell fastest in F1 qualifying", KEYWORDS) is True


def test_parse_articles_filters_irrelevant():
    rows = [
        {"url": "https://a.com/1", "title": "Verstappen wins the Grand Prix", "domain": "a.com"},
        {"url": "https://b.com/2", "title": "Local news about a person named Norris", "domain": "b.com"},
    ]
    items = parse_articles(rows, KEYWORDS)
    assert [i.url for i in items] == ["https://a.com/1"]
    assert items[0].source == "gdelt"


def test_parse_articles_tags_series():
    rows = [{"url": "https://a.com/1", "title": "Verstappen wins the Grand Prix", "domain": "a.com"}]
    items = parse_articles(rows, KEYWORDS, series="f1")
    assert items[0].series == "f1"


def test_spike_ratio_computes_last_over_mean():
    assert spike_ratio([10, 10, 10, 30]) == 3.0
    assert spike_ratio([]) == 1.0
    assert spike_ratio([5]) == 1.0
