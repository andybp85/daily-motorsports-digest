from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from digest.models import RawItem, SeriesDef

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

    kept = [(k, v) for k, v in parse_qsl(parsed.query) if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_KEYS]
    query = urlencode(kept)

    return urlunparse((scheme, netloc, path, "", query, ""))


def classify_series(title: str, source_series: str, registry: tuple[SeriesDef, ...]) -> str:
    """Return a followed series id, or '' — source hint wins, else first term match.

    Registry order is priority: a title matching two series resolves to the
    earlier one (the core series lead), so shared driver/manufacturer names
    fall to F1/IndyCar rather than an endurance series.
    """
    if source_series:
        return source_series
    low = title.lower()
    for series in registry:
        if any(term.lower() in low for term in series.terms):
            return series.id
    return ""


def is_relevant(title: str, registry: tuple[SeriesDef, ...]) -> bool:
    """Keep iff the title classifies to a followed series.

    This is the leak fix: a story is relevant only because it matches a series
    we chose, not because it happens to name a manufacturer or a generic
    motorsport word shared across series.
    """
    return classify_series(title, "", registry) != ""


def normalize_items(items: list[RawItem], registry: tuple[SeriesDef, ...]) -> list[RawItem]:
    """Return new items with canonical URL, extracted domain, and resolved series.

    Drops items that don't classify to a followed series — without this gate the
    general motorsport feeds (autosport, motorsport.com…) leak every series they
    carry into the digest.
    """
    out = []
    for it in items:
        series = classify_series(it.title, it.series, registry)
        if not series:
            continue
        url = canonicalize_url(it.url)
        domain = urlparse(url).netloc
        out.append(
            RawItem(
                source=it.source,
                url=url,
                title=it.title.strip(),
                domain=domain,
                published_at=it.published_at,
                reddit_score=it.reddit_score,
                reddit_comments=it.reddit_comments,
                series=series,
                extra=it.extra,
            )
        )
    return out
