import argparse
from datetime import UTC, date, datetime, timedelta

import anthropic
import boto3
import praw

from digest.collect import bluesky
from digest.collect.gdelt import fetch_gdelt
from digest.collect.reddit import fetch_reddit
from digest.collect.rss import fetch_rss
from digest.config import Config, load_config
from digest.email import render_html, render_subject, send_email
from digest.gate import filter_stories
from digest.pipeline import score_pool
from digest.state import StateStore
from digest.summarize import summarize


def _collect(cfg, since, end):
    """Gather raw items from all three sources plus GDELT spike ratios."""
    items = []
    items += fetch_rss(cfg.rss_feeds, since)

    gdelt_items, spikes = fetch_gdelt(cfg.keywords, since, end)
    items += gdelt_items

    items += _collect_reddit(cfg)

    return items, spikes


def _collect_reddit(cfg):
    """Pull Reddit items, or skip cleanly when disabled or unconfigured.

    Reddit's Responsible Builder Policy (late 2025) gates new API OAuth tokens
    behind manual approval, so fresh installs often have no working creds. Reddit
    is only one ranking signal — the digest runs on RSS + GDELT without it.
    """
    if not cfg.reddit_enabled:
        print("[reddit] disabled via config (reddit_enabled = false) — skipping")
        return []
    if not (cfg.reddit_client_id and cfg.reddit_client_secret and cfg.reddit_user_agent):
        print("[reddit] no credentials configured — skipping")
        return []

    reddit = praw.Reddit(client_id=cfg.reddit_client_id,
                         client_secret=cfg.reddit_client_secret,
                         user_agent=cfg.reddit_user_agent)
    return fetch_reddit(reddit, cfg.subreddits)


def _bluesky_client(cfg: Config) -> bluesky.BlueskyClient | None:
    """A logged-in BlueskyClient, or None when disabled/unconfigured/auth fails."""
    if not cfg.bluesky_enabled:
        print("[bluesky] disabled via config (bluesky_enabled = false) — skipping")
        return None
    if not (cfg.bsky_handle and cfg.bsky_app_password):
        print("[bluesky] no credentials configured — skipping")
        return None
    try:
        return bluesky.BlueskyClient(cfg.bsky_handle, cfg.bsky_app_password)
    except Exception as exc:                        # noqa: BLE001 — degrade, never crash the run
        print(f"[bluesky] auth failed: {exc} — skipping")
        return None


def run(config_path: str | None, dry_run: bool) -> None:
    cfg = load_config(config_path)
    end = datetime.now(UTC)
    since = end - timedelta(days=1)

    state = StateStore(cfg.db_path)
    try:
        raw, spikes = _collect(cfg, since, end)
        client_bsky = _bluesky_client(cfg)
        enrich = (lambda stories: bluesky.enrich(stories, client_bsky)) if client_bsky else None
        scored = score_pool(raw, spikes, cfg, enrich=enrich)          # full pre-gate pool, sorted desc
        survivors = filter_stories(
            scored, state,
            threshold=cfg.threshold, calibration=cfg.calibration,
            suppress_days=cfg.suppress_days, escalation_factor=cfg.escalation_factor,
        )
        top = survivors[: cfg.max_stories]

        if cfg.calibration and scored:
            print("[calibration] day's scores: "
                  + ", ".join(f"{s.buzz:.3f}" for s in scored[:20]))

        if not top:
            print(f"[digest] nothing cleared the gate (top buzz {scored[0].buzz:.3f} "
                  f"of {len(scored)} scored) — no email sent" if scored
                  else "[digest] no stories at all — no email sent")
            return

        if dry_run:
            print(f"[dry-run] {len(top)} stories would be sent:")
            for n, s in enumerate(top, 1):
                print(f"  {n}. [{s.buzz:.3f}] {s.story.title}  ({len(s.story.domains)} outlets)")
            return

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        blurbs = summarize(client, top, cfg.model)

        today = date.today()
        html = render_html(blurbs, today)
        ses = boto3.client("ses", region_name=cfg.aws_region)
        send_email(ses, cfg.ses_sender, cfg.ses_recipient, render_subject(today), html)

        for s in top:
            state.record_sent(s.story.key, s.buzz, end)
        print(f"[digest] sent {len(top)} stories")
    finally:
        state.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="F1/IndyCar morning buzz digest")
    parser.add_argument("--config", default=None, help="path to config.toml")
    parser.add_argument("--dry-run", action="store_true",
                        help="rank and print, but don't summarize or send")
    args = parser.parse_args()
    run(args.config, args.dry_run)


if __name__ == "__main__":
    main()
