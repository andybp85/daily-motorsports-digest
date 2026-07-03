from digest.cluster import cluster_items, story_key
from digest.models import RawItem


def _item(source, url, title, domain, series="f1", score=0, comments=0):
    return RawItem(source=source, url=url, title=title, domain=domain,
                   series=series, reddit_score=score, reddit_comments=comments)


def test_story_key_is_stable_and_url_dependent():
    a = story_key("https://x.com/a", "Some Title")
    b = story_key("https://x.com/a", "Some Title")
    c = story_key("https://x.com/b", "Some Title")
    assert a == b
    assert a != c


def test_same_url_across_sources_clusters_into_one_story():
    items = [
        _item("rss", "https://autosport.com/story", "Verstappen wins", "autosport.com"),
        _item("reddit", "https://autosport.com/story", "Verstappen wins", "reddit.com",
              score=4200, comments=900),
    ]
    stories = cluster_items(items)
    assert len(stories) == 1
    assert len(stories[0].items) == 2


def test_fuzzy_title_match_clusters_syndicated_versions():
    items = [
        _item("rss", "https://autosport.com/a", "Verstappen to Mercedes rumor resurfaces", "autosport.com"),
        _item("rss", "https://motorsport.com/b", "Verstappen to Mercedes rumour resurfaces", "motorsport.com"),
    ]
    stories = cluster_items(items)
    assert len(stories) == 1
    assert stories[0].domains == {"autosport.com", "motorsport.com"}


def test_distinct_stories_stay_separate():
    items = [
        _item("rss", "https://a.com/1", "Iowa doubleheader preview", "a.com"),
        _item("rss", "https://b.com/2", "Verstappen wins in Austria", "b.com"),
    ]
    stories = cluster_items(items)
    assert len(stories) == 2
