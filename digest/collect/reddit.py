from digest.models import RawItem


def parse_submission(submission, series: str) -> RawItem:
    """Convert a PRAW submission into a RawItem."""
    return RawItem(
        source="reddit",
        url=submission.url,
        title=submission.title,
        reddit_score=int(submission.score),
        reddit_comments=int(submission.num_comments),
        series=series,
        extra={"permalink": f"https://reddit.com{submission.permalink}"},
    )


def fetch_reddit(reddit, subreddits: list[dict], limit: int = 50) -> list[RawItem]:
    """Pull top-of-day submissions from each configured subreddit."""
    items = []
    for sub in subreddits:
        try:
            for submission in reddit.subreddit(sub["name"]).top(time_filter="day", limit=limit):
                items.append(parse_submission(submission, sub.get("series", "")))
        except Exception as exc:                    # noqa: BLE001 — one subreddit must not kill the run
            print(f"[reddit] failed r/{sub.get('name')}: {exc}")
    return items
