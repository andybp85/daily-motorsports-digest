import hashlib

from rapidfuzz import fuzz

from digest.models import RawItem, Story


def story_key(canonical_url: str, title: str) -> str:
    """Stable identity for a story: canonical URL + a short hash of the title."""
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:10]
    return f"{canonical_url}#{h}"


def cluster_items(items: list[RawItem], title_threshold: int = 88) -> list[Story]:
    """Group items into stories by canonical-URL match OR fuzzy title match."""
    clusters: list[list[RawItem]] = []
    for it in items:
        placed = False
        for cluster in clusters:
            head = cluster[0]
            if it.url == head.url or fuzz.token_sort_ratio(it.title, head.title) >= title_threshold:
                cluster.append(it)
                placed = True
                break
        if not placed:
            clusters.append([it])

    stories = []
    for cluster in clusters:
        head = cluster[0]
        series = _majority_series(cluster)
        stories.append(Story(
            key=story_key(head.url, head.title),
            canonical_url=head.url,
            title=head.title,
            series=series,
            items=cluster,
        ))
    return stories


def _majority_series(cluster: list[RawItem]) -> str:
    counts: dict[str, int] = {}
    for it in cluster:
        if it.series:
            counts[it.series] = counts.get(it.series, 0) + 1
    if not counts:
        return ""
    return max(counts, key=counts.get)
