from typing import Protocol

from digest.models import ScoredStory


class SentHistory(Protocol):
    """The slice of the state store the gate depends on."""

    def last_sent(self, key: str, within_days: int) -> float | None:
        ...


def filter_stories(scored: list[ScoredStory], state: SentHistory, *, threshold: float,
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
