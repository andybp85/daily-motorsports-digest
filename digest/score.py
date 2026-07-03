from digest.models import ScoredStory, Story


def rank_normalize(values: list[float]) -> list[float]:
    """Map values to 0..1 by rank within the pool. Ties share the same rank position."""
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [1.0]
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    for position, idx in enumerate(order):
        ranks[idx] = position / (n - 1)
    return ranks


def _reddit_signal(story: Story) -> float:
    return float(sum(i.reddit_score + i.reddit_comments for i in story.items))


def score_stories(stories: list[Story], series_spike: dict[str, float],
                  weights: dict[str, float]) -> list[ScoredStory]:
    """Rank-normalize each signal within the pool, then weighted-sum into buzz."""
    if not stories:
        return []

    reddit_raw = [_reddit_signal(s) for s in stories]
    breadth_raw = [float(len(s.domains)) for s in stories]
    spike_raw = [series_spike.get(s.series, 1.0) for s in stories]

    reddit_rank = rank_normalize(reddit_raw)
    breadth_rank = rank_normalize(breadth_raw)
    spike_rank = rank_normalize(spike_raw)

    scored = []
    for i, story in enumerate(stories):
        buzz = (weights["reddit"] * reddit_rank[i]
                + weights["breadth"] * breadth_rank[i]
                + weights["spike"] * spike_rank[i])
        scored.append(ScoredStory(
            story=story, reddit_raw=reddit_raw[i], breadth_raw=breadth_raw[i],
            spike_raw=spike_raw[i], buzz=buzz,
        ))
    scored.sort(key=lambda s: s.buzz, reverse=True)
    return scored
