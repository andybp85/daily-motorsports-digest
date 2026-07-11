import re

from digest.models import Story


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
