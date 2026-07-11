from digest.collect.bluesky import (
    engagement,
    enrich,
    external_uri,
    match_posts,
    normalize_url,
    post_links_story,
)
from digest.models import RawItem, Story


def _story(url: str) -> Story:
    return Story(key="k", canonical_url=url, title="Verstappen wins at Spa",
                 series="f1", items=[RawItem(source="rss", url=url, title="t", domain="d")])


def _post(uri: str = "", text: str = "", likes: int = 0, reposts: int = 0, replies: int = 0) -> dict:
    embed = {"$type": "app.bsky.embed.external", "external": {"uri": uri}} if uri else {}
    return {"record": {"text": text, "embed": embed},
            "likeCount": likes, "repostCount": reposts, "replyCount": replies}


def test_normalize_url_strips_scheme_www_query_slash():
    assert normalize_url("https://www.Autosport.com/f1/news/x/?utm=1#top") == "autosport.com/f1/news/x"
    assert normalize_url("http://the-race.com/feed/") == "the-race.com/feed"


def test_external_uri_reads_embed_or_empty():
    assert external_uri(_post(uri="https://a.com/1")) == "https://a.com/1"
    assert external_uri(_post(text="no embed")) == ""


def test_post_links_story_matches_embed_or_raw_link():
    story = _story("https://autosport.com/f1/news/x")
    assert post_links_story(_post(uri="https://www.autosport.com/f1/news/x/"), story.canonical_url)
    assert post_links_story(_post(text="great read https://autosport.com/f1/news/x"), story.canonical_url)
    assert not post_links_story(_post(uri="https://other.com/y", text="off topic"), story.canonical_url)


def test_post_links_story_rejects_longer_slug_at_same_domain():
    story = _story("https://autosport.com/f1/news/x")
    post = _post(text="great read https://autosport.com/f1/news/x-crash-report")
    assert not post_links_story(post, story.canonical_url)


def test_post_links_story_rejects_lookalike_domain():
    story = _story("https://autosport.com/f1/news/x")
    post = _post(text="great read https://fakeautosport.com/f1/news/x")
    assert not post_links_story(post, story.canonical_url)


def test_post_links_story_matches_exact_raw_link():
    story = _story("https://autosport.com/f1/news/x")
    post = _post(text="great read https://autosport.com/f1/news/x")
    assert post_links_story(post, story.canonical_url)


def test_match_posts_filters_to_linking_posts():
    story = _story("https://autosport.com/f1/news/x")
    posts = [_post(uri="https://autosport.com/f1/news/x", likes=5),
             _post(uri="https://other.com/y", likes=99)]
    assert [p["likeCount"] for p in match_posts(story, posts)] == [5]


def test_engagement_sums_like_repost_reply():
    assert engagement([_post(likes=3, reposts=2, replies=1), _post(likes=10)]) == 16


class _FakeClient:
    """Returns canned search results keyed by whether the query is the story URL."""

    def __init__(self, by_query: dict):
        self.by_query = by_query
        self.calls = []

    def search_posts(self, query, *, limit=100, sort="top"):
        self.calls.append(query)
        return self.by_query.get(query, [])


def test_enrich_appends_engagement_item_for_linked_story():
    url = "https://autosport.com/f1/news/x"
    story = _story(url)
    client = _FakeClient({url: [_post(uri=url, likes=4, reposts=1, replies=2)]})

    (out,) = enrich([story], client)

    bsky_items = [i for i in out.items if i.source == "bluesky"]
    assert len(bsky_items) == 1
    assert bsky_items[0].reddit_score == 7          # 4 + 1 + 2


def test_enrich_falls_back_to_title_search_when_url_search_empty():
    url = "https://autosport.com/f1/news/x"
    story = _story(url)                              # title "Verstappen wins at Spa"
    client = _FakeClient({"Verstappen wins Spa": [_post(uri=url, likes=5)]})

    (out,) = enrich([story], client)

    assert any(i.source == "bluesky" and i.reddit_score == 5 for i in out.items)


def test_enrich_leaves_unlinked_story_untouched():
    story = _story("https://autosport.com/f1/news/x")
    client = _FakeClient({})                         # no posts for anything

    (out,) = enrich([story], client)

    assert not any(i.source == "bluesky" for i in out.items)


def test_enrich_no_client_is_noop():
    story = _story("https://autosport.com/f1/news/x")
    (out,) = enrich([story], None)
    assert not any(i.source == "bluesky" for i in out.items)


def test_enrich_one_story_failure_does_not_kill_run():
    class _Boom:
        def search_posts(self, *a, **k):
            raise RuntimeError("network down")
    story = _story("https://autosport.com/f1/news/x")
    (out,) = enrich([story], _Boom())                # must not raise
    assert not any(i.source == "bluesky" for i in out.items)
