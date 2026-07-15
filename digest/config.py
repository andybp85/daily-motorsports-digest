import os
import tomllib
from dataclasses import dataclass, field

from digest.models import SeriesDef, Tier

_DEFAULT_TIER_SERIES = frozenset({"f1", "indycar"})
_DEFAULT_TIER_FLOOR = 6


@dataclass
class Config:
    model: str = "claude-haiku-4-5"
    threshold: float = 0.0
    calibration: bool = True
    suppress_days: int = 3
    escalation_factor: float = 1.5
    db_path: str = "state.db"
    timezone: str = "America/New_York"
    max_stories: int = 15
    reddit_enabled: bool = True
    weights: dict = field(default_factory=lambda: {"social": 0.5, "breadth": 0.35, "spike": 0.15})
    ses_sender: str = ""
    ses_recipient: str = ""
    aws_region: str = "us-east-1"
    rss_feeds: list = field(default_factory=list)
    subreddits: list = field(default_factory=list)
    series: tuple[SeriesDef, ...] = ()
    tiers: tuple[Tier, ...] = (Tier(series=_DEFAULT_TIER_SERIES, floor=_DEFAULT_TIER_FLOOR),)
    # Secrets (from env)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    anthropic_api_key: str = ""
    bluesky_enabled: bool = False
    bsky_handle: str = ""
    bsky_app_password: str = ""


def _parse_series(raw: list[dict]) -> tuple[SeriesDef, ...]:
    """Build the series registry from [[series]] blocks, preserving order."""
    return tuple(SeriesDef(id=b["id"], label=b["label"], terms=tuple(b["terms"])) for b in raw)


def _parse_tiers(raw: list[dict], max_stories: int) -> tuple[Tier, ...]:
    """Build the priority tiers from [[tier]] blocks; default to one core tier.

    Floors are honored in order, so tier position encodes priority. The summed
    floor must fit the cap — an oversubscribed config is a mistake, not a thing
    to silently clamp, so it raises.
    """
    tiers = tuple(Tier(series=frozenset(t["series"]), floor=int(t["floor"])) for t in raw)
    if not tiers:
        tiers = (Tier(series=_DEFAULT_TIER_SERIES, floor=min(_DEFAULT_TIER_FLOOR, max_stories)),)

    total = sum(t.floor for t in tiers)
    if total > max_stories:
        raise ValueError(f"tier floors sum to {total}, exceeding max_stories ({max_stories})")
    return tiers


def load_config(path: str | None = None) -> Config:
    """Load config from a TOML file (path or ./config.toml) plus secrets from env."""
    path = path or "config.toml"
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    series = _parse_series(data.get("series", []))
    max_stories = int(data.get("max_stories", 15))
    tiers = _parse_tiers(data.get("tier", []), max_stories)

    if series:  # validate tier membership only once the registry is populated
        known = {s.id for s in series}
        unknown = sorted({sid for tier in tiers for sid in tier.series if sid not in known})
        if unknown:
            raise ValueError(f"tier references unknown series id(s): {unknown}")

    ses = data.get("ses", {})
    cfg = Config(
        model=data.get("model", "claude-haiku-4-5"),
        threshold=float(data.get("threshold", 0.0)),
        calibration=bool(data.get("calibration", True)),
        suppress_days=int(data.get("suppress_days", 3)),
        escalation_factor=float(data.get("escalation_factor", 1.5)),
        db_path=data.get("db_path", "state.db"),
        timezone=data.get("timezone", "America/New_York"),
        max_stories=max_stories,
        reddit_enabled=bool(data.get("reddit_enabled", True)),
        weights=data.get("weights", {"social": 0.5, "breadth": 0.35, "spike": 0.15}),
        ses_sender=ses.get("sender", ""),
        ses_recipient=ses.get("recipient", ""),
        aws_region=ses.get("aws_region", "us-east-1"),
        rss_feeds=data.get("rss_feeds", []),
        subreddits=data.get("subreddits", []),
        series=series,
        tiers=tiers,
        reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        bluesky_enabled=bool(data.get("bluesky_enabled", False)),
        bsky_handle=os.environ.get("BSKY_HANDLE", ""),
        bsky_app_password=os.environ.get("BSKY_APP_PASSWORD", ""),
    )
    return cfg
