import json
import re
import urllib.parse
import urllib.request

from digest.models import RawItem, Story


def normalize_url(url: str) -> str:
    """Comparison form: lowercase, no scheme/www, no query/fragment, no trailing slash."""
    stripped = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
    stripped = stripped.split("?")[0].split("#")[0]
    return stripped.rstrip("/")


def external_uri(post: dict) -> str:
    """The article URI from a post's external embed, or '' when there is none."""
    embed = post.get("record", {}).get("embed", {}) or {}
    if str(embed.get("$type", "")).startswith("app.bsky.embed.external"):
        return embed.get("external", {}).get("uri", "")
    return ""


def post_links_story(post: dict, story_url: str) -> bool:
    """True if the post links the story's article via embed card or a raw link in text."""
    target = normalize_url(story_url)
    if not target:
        return False
    if normalize_url(external_uri(post)) == target:
        return True
    text = post.get("record", {}).get("text", "") or ""
    return any(normalize_url(u) == target for u in re.findall(r"https?://\S+", text))


def match_posts(story: Story, posts: list[dict]) -> list[dict]:
    """Posts (from a search) that actually link the story's article."""
    return [p for p in posts if post_links_story(p, story.canonical_url)]


def engagement(posts: list[dict]) -> int:
    """Total like + repost + reply across posts."""
    return sum(p.get("likeCount", 0) + p.get("repostCount", 0) + p.get("replyCount", 0)
               for p in posts)


_BSKY_API = "https://bsky.social/xrpc"


class BlueskyClient:
    """Thin authenticated wrapper over the Bluesky search endpoint (stdlib only).

    Each HTTP call is bounded by `timeout` so a stalled endpoint can't hang the
    digest — the same failure mode fixed for GDELT.
    """

    def __init__(self, handle: str, app_password: str, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._token = self._create_session(handle, app_password)

    def _create_session(self, identifier: str, password: str) -> str:
        body = json.dumps({"identifier": identifier, "password": password}).encode()
        req = urllib.request.Request(
            f"{_BSKY_API}/com.atproto.server.createSession",
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.load(resp)["accessJwt"]

    def search_posts(self, query: str, *, limit: int = 100, sort: str = "top") -> list[dict]:
        params = urllib.parse.urlencode({"q": query, "limit": limit, "sort": sort})
        req = urllib.request.Request(
            f"{_BSKY_API}/app.bsky.feed.searchPosts?{params}",
            headers={"Authorization": f"Bearer {self._token}"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.load(resp).get("posts", [])


def _title_terms(title: str, n: int = 6) -> str:
    """A few significant words from the headline for a text search."""
    words = [w for w in re.findall(r"[A-Za-z0-9']+", title) if len(w) > 2]
    return " ".join(words[:n])


def _story_posts(story: Story, client: object) -> list[dict]:
    """Posts linking the story: direct URL search first, title-terms fallback."""
    hits = match_posts(story, client.search_posts(story.canonical_url, sort="latest"))
    if hits:
        return hits
    return match_posts(story, client.search_posts(_title_terms(story.title)))


def enrich(stories: list[Story], client: object | None) -> list[Story]:
    """Attach a synthetic Bluesky engagement item to each story with linking posts.

    No-op when `client` is None. One story's search failure is logged and skipped
    so it cannot kill the run.
    """
    if client is None:
        return stories
    for story in stories:
        try:
            posts = _story_posts(story, client)
        except Exception as exc:                    # noqa: BLE001 — one story must not kill the run
            print(f"[bluesky] search failed for {story.canonical_url}: {exc}")
            continue
        if not posts:
            continue
        story.items.append(RawItem(
            source="bluesky", url=story.canonical_url, title=story.title,
            reddit_score=engagement(posts), series=story.series,
        ))
    return stories
