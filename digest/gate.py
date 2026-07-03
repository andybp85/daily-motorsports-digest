from digest.models import ScoredStory


def filter_stories(scored: list[ScoredStory], state, *, threshold: float,
                   calibration: bool, suppress_days: int,
                   escalation_factor: float) -> list[ScoredStory]:
    """Drop below-threshold and recently-sent stories (unless escalated)."""
    survivors = []
    for s in scored:
        if not calibration and s.buzz < threshold:
            continue

        last = state.last_sent(s.story.key, suppress_days)
        if last is not None and s.buzz < last * escalation_factor:
            continue          # sent recently and not escalated → suppress

        survivors.append(s)
    return survivors
