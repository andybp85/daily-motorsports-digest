from digest.collect.bluesky import (
    engagement,
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


def test_match_posts_filters_to_linking_posts():
    story = _story("https://autosport.com/f1/news/x")
    posts = [_post(uri="https://autosport.com/f1/news/x", likes=5),
             _post(uri="https://other.com/y", likes=99)]
    assert [p["likeCount"] for p in match_posts(story, posts)] == [5]


def test_engagement_sums_like_repost_reply():
    assert engagement([_post(likes=3, reposts=2, replies=1), _post(likes=10)]) == 16
