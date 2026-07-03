from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from digest.models import RawItem

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "cmpid"}


def canonicalize_url(url: str) -> str:
    """Lowercase host, strip tracking params + fragment, normalize AMP + trailing slash."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()

    path = parsed.path
    if path.endswith("/amp/"):
        path = path[:-5]
    elif path.endswith("/amp"):
        path = path[:-4]

    path = path or "/"

    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    kept = [(k, v) for k, v in parse_qsl(parsed.query)
            if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_KEYS]
    query = urlencode(kept)

    return urlunparse((scheme, netloc, path, "", query, ""))


def classify_series(title: str, source_series: str, keywords: dict) -> str:
    """Return 'f1' | 'indycar' | '' — source hint wins, else classify from title."""
    if source_series:
        return source_series
    low = title.lower()
    if any(k.lower() in low for k in keywords.get("series_indycar", [])):
        return "indycar"
    if any(k.lower() in low for k in keywords.get("series_f1", [])):
        return "f1"
    return ""


def normalize_items(items: list[RawItem], keywords: dict) -> list[RawItem]:
    """Return new items with canonical URL, extracted domain, and resolved series."""
    out = []
    for it in items:
        url = canonicalize_url(it.url)
        domain = urlparse(url).netloc
        series = classify_series(it.title, it.series, keywords)
        out.append(RawItem(
            source=it.source, url=url, title=it.title.strip(), domain=domain,
            published_at=it.published_at, reddit_score=it.reddit_score,
            reddit_comments=it.reddit_comments, series=series, extra=it.extra,
        ))
    return out
