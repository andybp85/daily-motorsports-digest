from types import SimpleNamespace

from digest.collect.reddit import fetch_reddit, parse_submission


def _submission(title, url, score, comments, permalink="/r/formula1/abc"):
    return SimpleNamespace(title=title, url=url, score=score, num_comments=comments,
                           permalink=permalink)


def test_parse_submission_maps_fields():
    sub = _submission("Verstappen wins", "https://autosport.com/x", 4200, 900)
    item = parse_submission(sub, "f1")
    assert item.source == "reddit"
    assert item.url == "https://autosport.com/x"
    assert item.title == "Verstappen wins"
    assert item.reddit_score == 4200
    assert item.reddit_comments == 900
    assert item.series == "f1"


class FakeSubreddit:
    def __init__(self, subs):
        self._subs = subs

    def top(self, time_filter, limit):
        assert time_filter == "day"
        return self._subs[:limit]


class FakeReddit:
    def __init__(self, mapping):
        self._mapping = mapping

    def subreddit(self, name):
        return FakeSubreddit(self._mapping[name])


def test_fetch_reddit_pulls_each_configured_subreddit():
    reddit = FakeReddit({
        "formula1": [_submission("F1 story", "https://a/1", 100, 10)],
        "IndyCar": [_submission("Indy story", "https://b/2", 50, 5)],
    })
    subs = [{"name": "formula1", "series": "f1"}, {"name": "IndyCar", "series": "indycar"}]

    items = fetch_reddit(reddit, subs, limit=25)

    assert {i.series for i in items} == {"f1", "indycar"}
    assert len(items) == 2
