from datetime import datetime

from digest.models import RawItem


def build_keyword_list(keywords: dict, kind: str) -> list[str]:
    """Series + team + driver terms scoped to one series ('f1' or 'indycar')."""
    series_key = "series_f1" if kind == "f1" else "series_indycar"
    return (list(keywords.get(series_key, []))
            + list(keywords.get("teams", []))
            + list(keywords.get("drivers", [])))


def is_relevant(title: str, keywords: dict) -> bool:
    """Keep if the title has a series/team term, or a driver name WITH a motorsport anchor."""
    low = title.lower()
    series_terms = keywords.get("series_f1", []) + keywords.get("series_indycar", [])
    if any(t.lower() in low for t in series_terms + keywords.get("teams", [])):
        return True
    has_driver = any(d.lower() in low for d in keywords.get("drivers", []))
    has_anchor = any(a.lower() in low for a in keywords.get("anchors", []))
    return has_driver and has_anchor


def parse_articles(rows: list[dict], keywords: dict) -> list[RawItem]:
    """Convert GDELT article rows into relevant RawItems."""
    items = []
    for row in rows:
        title = row.get("title", "")
        if not is_relevant(title, keywords):
            continue
        items.append(RawItem(
            source="gdelt",
            url=row.get("url", ""),
            title=title,
            domain=row.get("domain", ""),
        ))
    return items


def spike_ratio(volumes: list[float]) -> float:
    """Last window's volume divided by the mean of prior windows. Default 1.0."""
    if len(volumes) < 2:
        return 1.0
    prior = volumes[:-1]
    mean_prior = sum(prior) / len(prior)
    if mean_prior == 0:
        return 1.0
    return volumes[-1] / mean_prior


def fetch_gdelt(keywords: dict, since: datetime, end: datetime, client=None):
    """Return (articles, {'f1': ratio, 'indycar': ratio}). Thin glue over the pure helpers.

    Verify gdeltdoc column names against the installed version before relying on this.
    """
    from gdeltdoc import Filters, GdeltDoc

    gd = client or GdeltDoc()
    fmt = "%Y-%m-%d"
    start_s, end_s = since.strftime(fmt), end.strftime(fmt)

    articles: list[RawItem] = []
    spikes: dict[str, float] = {}
    for kind in ("f1", "indycar"):
        try:
            filt = Filters(keyword=build_keyword_list(keywords, kind),
                           start_date=start_s, end_date=end_s, num_records=250)
            df = gd.article_search(filt)
            rows = df.to_dict("records") if df is not None and not df.empty else []
            articles.extend(parse_articles(rows, keywords))

            tl = gd.timeline_search("timelinevol", filt)
            vols = tl.iloc[:, -1].tolist() if tl is not None and not tl.empty else []
            spikes[kind] = spike_ratio([float(v) for v in vols])
        except Exception as exc:                    # noqa: BLE001 — one series must not kill the run
            print(f"[gdelt] failed {kind}: {exc}")
            spikes[kind] = 1.0
    return articles, spikes
