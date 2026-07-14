import signal
import socket
import time
from contextlib import contextmanager
from datetime import datetime

from digest.models import RawItem, SeriesDef
from digest.normalize import is_relevant

_GDELT_CALL_TIMEOUT_S = 30.0


class GdeltTimeout(Exception):
    """A single GDELT HTTP call exceeded its wall-clock budget."""


@contextmanager
def _time_limit(seconds: float):
    """Abort the wrapped block if it runs longer than `seconds`.

    gdeltdoc issues requests.get() with no timeout, so a stalled GDELT
    connection hangs forever and the daily run never reaches the email step.
    SIGALRM interrupts the blocking socket read on the main thread (the
    digest's only thread on the systemd deploy), turning a hang into an
    exception the caller already degrades on. Unix-only, which the deploy
    and tests both are.
    """

    def _raise(_signum: int, _frame: object) -> None:
        raise GdeltTimeout(f"GDELT call exceeded {seconds:g}s")

    previous = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


@contextmanager
def _prefer_ipv4():
    """Try IPv4 before IPv6 for the wrapped block.

    Some networks black-hole the IPv6 route to api.gdeltproject.org (observed
    on the Pi deploy: `curl -6` fails, `curl -4` works). Python's requests/
    urllib3 walk getaddrinfo results in order and stall on the dead IPv6
    attempt until the SIGALRM timeout fires, so GDELT contributes nothing.
    Sorting IPv4 first lets the working address win the connect; IPv6 stays
    as a fallback for hosts where IPv4 is the broken path. A host-level
    /etc/gai.conf preference did not reach CPython's resolver, so we set it
    in-process. Global but short-lived — safe because the digest is
    single-threaded and GDELT is the only caller in this window.
    """
    resolve = socket.getaddrinfo

    def ipv4_first(*args: object, **kwargs: object) -> list:
        return sorted(resolve(*args, **kwargs), key=lambda row: row[0] != socket.AF_INET)

    socket.getaddrinfo = ipv4_first
    try:
        yield
    finally:
        socket.getaddrinfo = resolve


def build_keyword_list(registry: tuple[SeriesDef, ...], kind: str) -> list[str]:
    """The terms for one series id ('f1' | 'indycar'), or [] if not followed.

    Deliberately short: GDELT rejects an over-long keyword query, so we send one
    series' identifying terms and let is_relevant() do fine filtering downstream.
    """
    for series in registry:
        if series.id == kind:
            return list(series.terms)
    return []


def parse_articles(rows: list[dict], registry: tuple[SeriesDef, ...], series: str = "") -> list[RawItem]:
    """Convert GDELT article rows into relevant RawItems."""
    items = []
    for row in rows:
        title = row.get("title", "")
        if not is_relevant(title, registry):
            continue
        items.append(
            RawItem(
                source="gdelt",
                url=row.get("url", ""),
                title=title,
                domain=row.get("domain", ""),
                series=series,
            )
        )
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


def _search_with_retry(
    search,
    *,
    attempts: int = 4,
    delay: float = 5.0,
    timeout: float = _GDELT_CALL_TIMEOUT_S,
):
    """Run a GDELT search callable, retrying on rate-limit with linear backoff.

    GDELT throttles to roughly one request per 5s. A daily run makes only a
    handful of calls, so a few spaced retries clear the transient 429s that
    otherwise surface as an empty-message RateLimitError.

    Each attempt is bounded by `timeout`: a wedged connection raises GdeltTimeout
    rather than blocking forever. That is not retried — it propagates to the
    caller, which degrades to neutral spikes and no articles for the series.

    IPv4 is preferred over IPv6 for the call: some deploys can't reach GDELT
    over IPv6 and would otherwise stall until the timeout (see _prefer_ipv4).
    """
    from gdeltdoc.errors import RateLimitError

    for attempt in range(attempts):
        try:
            with _prefer_ipv4(), _time_limit(timeout):
                return search()
        except RateLimitError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay * (attempt + 1))


def fetch_gdelt(
    registry: tuple[SeriesDef, ...],
    since: datetime,
    end: datetime,
    client=None,
    timeout: float = _GDELT_CALL_TIMEOUT_S,
) -> tuple[list[RawItem], dict[str, float]]:
    """Return (articles, {'f1': ratio, 'indycar': ratio}). Thin glue over the pure helpers.

    Each GDELT call is capped at `timeout` seconds so a stalled endpoint can't
    hang the daily run. Verify gdeltdoc column names against the installed
    version before relying on this.
    """
    from gdeltdoc import Filters, GdeltDoc

    gd = client or GdeltDoc()
    fmt = "%Y-%m-%d"
    start_s, end_s = since.strftime(fmt), end.strftime(fmt)

    articles: list[RawItem] = []
    spikes: dict[str, float] = {}
    for kind in ("f1", "indycar"):
        try:
            filt = Filters(
                keyword=build_keyword_list(registry, kind),
                start_date=start_s,
                end_date=end_s,
                num_records=250,
            )
            df = _search_with_retry(lambda: gd.article_search(filt), timeout=timeout)
            rows = df.to_dict("records") if df is not None and not df.empty else []
            articles.extend(parse_articles(rows, registry, series=kind))

            tl = _search_with_retry(lambda: gd.timeline_search("timelinevol", filt), timeout=timeout)
            vols = tl.iloc[:, -1].tolist() if tl is not None and not tl.empty else []
            spikes[kind] = spike_ratio([float(v) for v in vols])
        except Exception as exc:  # noqa: BLE001 — one series must not kill the run
            print(f"[gdelt] failed {kind}: {exc}")
            spikes[kind] = 1.0
    return articles, spikes
