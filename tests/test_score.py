from digest.models import RawItem, Story
from digest.score import rank_normalize, score_stories

WEIGHTS = {"reddit": 0.5, "breadth": 0.35, "spike": 0.15}


def test_rank_normalize_maps_to_zero_one():
    assert rank_normalize([10, 20, 30]) == [0.0, 0.5, 1.0]


def test_rank_normalize_handles_single_value():
    assert rank_normalize([42]) == [1.0]


def test_rank_normalize_handles_empty():
    assert rank_normalize([]) == []


def test_rank_normalize_ties_share_average_rank():
    assert rank_normalize([5, 5, 5]) == [0.5, 0.5, 0.5]
    assert rank_normalize([10, 10, 30]) == [0.25, 0.25, 1.0]


def _story(key, series, domains, reddit_score, reddit_comments):
    items = [RawItem(source="rss", url=f"https://{d}/x", title=key, domain=d, series=series)
             for d in domains]
    items[0].reddit_score = reddit_score
    items[0].reddit_comments = reddit_comments
    return Story(key=key, canonical_url=f"https://{domains[0]}/x", title=key,
                 series=series, items=items)


def test_score_stories_ranks_by_buzz_and_sorts_desc():
    big = _story("big", "f1", ["a.com", "b.com", "c.com"], 5000, 900)
    small = _story("small", "indycar", ["d.com"], 50, 5)
    spike = {"f1": 2.0, "indycar": 1.0}

    scored = score_stories([small, big], spike, WEIGHTS)

    assert [s.story.key for s in scored] == ["big", "small"]   # sorted desc
    assert scored[0].buzz > scored[1].buzz
    assert 0.0 <= scored[1].buzz <= 1.0


def test_score_uses_series_spike_lookup():
    s = _story("s", "f1", ["a.com"], 100, 10)
    scored = score_stories([s], {"f1": 3.0}, WEIGHTS)
    assert scored[0].spike_raw == 3.0
