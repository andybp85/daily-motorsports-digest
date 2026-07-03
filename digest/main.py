import argparse
from datetime import UTC, date, datetime, timedelta

import anthropic
import boto3
import praw

from digest.collect.gdelt import fetch_gdelt
from digest.collect.reddit import fetch_reddit
from digest.collect.rss import fetch_rss
from digest.config import load_config
from digest.email import render_html, render_subject, send_email
from digest.pipeline import rank
from digest.state import StateStore
from digest.summarize import summarize


def _collect(cfg, since, end):
    """Gather raw items from all three sources plus GDELT spike ratios."""
    items = []
    items += fetch_rss(cfg.rss_feeds, since)

    gdelt_items, spikes = fetch_gdelt(cfg.keywords, since, end)
    items += gdelt_items

    reddit = praw.Reddit(client_id=cfg.reddit_client_id,
                         client_secret=cfg.reddit_client_secret,
                         user_agent=cfg.reddit_user_agent)
    items += fetch_reddit(reddit, cfg.subreddits)

    return items, spikes


def run(config_path: str | None, dry_run: bool) -> None:
    cfg = load_config(config_path)
    end = datetime.now(UTC)
    since = end - timedelta(days=1)

    state = StateStore(cfg.db_path)
    try:
        raw, spikes = _collect(cfg, since, end)
        scored = rank(raw, spikes, state, cfg)
        top = scored[: cfg.max_stories]

        if not top:
            print(f"[digest] nothing cleared the gate (top buzz: "
                  f"{scored[0].buzz:.3f} of {len(scored)})" if scored
                  else "[digest] no stories at all — no email sent")
            return

        if cfg.calibration:
            print("[calibration] day's scores: "
                  + ", ".join(f"{s.buzz:.3f}" for s in scored[:20]))

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
