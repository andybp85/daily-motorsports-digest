import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Config:
    model: str = "claude-haiku-4-5"
    threshold: float = 0.0
    calibration: bool = True
    suppress_days: int = 3
    escalation_factor: float = 1.5
    db_path: str = "state.db"
    timezone: str = "America/New_York"
    max_stories: int = 8
    reddit_enabled: bool = True
    weights: dict = field(default_factory=lambda: {"social": 0.5, "breadth": 0.35, "spike": 0.15})
    ses_sender: str = ""
    ses_recipient: str = ""
    aws_region: str = "us-east-1"
    rss_feeds: list = field(default_factory=list)
    subreddits: list = field(default_factory=list)
    keywords: dict = field(default_factory=dict)
    # Secrets (from env)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    anthropic_api_key: str = ""
    bluesky_enabled: bool = False
    bsky_handle: str = ""
    bsky_app_password: str = ""


def load_config(path: str | None = None) -> Config:
    """Load config from a TOML file (path or ./config.toml) plus secrets from env."""
    path = path or "config.toml"
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    ses = data.get("ses", {})
    cfg = Config(
        model=data.get("model", "claude-haiku-4-5"),
        threshold=float(data.get("threshold", 0.0)),
        calibration=bool(data.get("calibration", True)),
        suppress_days=int(data.get("suppress_days", 3)),
        escalation_factor=float(data.get("escalation_factor", 1.5)),
        db_path=data.get("db_path", "state.db"),
        timezone=data.get("timezone", "America/New_York"),
        max_stories=int(data.get("max_stories", 8)),
        reddit_enabled=bool(data.get("reddit_enabled", True)),
        weights=data.get("weights", {"social": 0.5, "breadth": 0.35, "spike": 0.15}),
        ses_sender=ses.get("sender", ""),
        ses_recipient=ses.get("recipient", ""),
        aws_region=ses.get("aws_region", "us-east-1"),
        rss_feeds=data.get("rss_feeds", []),
        subreddits=data.get("subreddits", []),
        keywords=data.get("keywords", {}),
        reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
        bluesky_enabled=bool(data.get("bluesky_enabled", False)),
        bsky_handle=os.environ.get("BSKY_HANDLE", ""),
        bsky_app_password=os.environ.get("BSKY_APP_PASSWORD", ""),
    )
    return cfg
