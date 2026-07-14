from typing import Protocol

from digest.models import ScoredStory


class SentHistory(Protocol):
    """The slice of the state store the gate depends on."""

    def last_sent(self, key: str, within_days: int) -> float | None: ...


def filter_stories(
    scored: list[ScoredStory], state: SentHistory, *, threshold: float, calibration: bool, suppress_days: int, escalation_factor: float
) -> list[ScoredStory]:
    """Drop below-threshold and recently-sent stories (unless escalated)."""
    survivors = []
    for s in scored:
        if not calibration and s.buzz < threshold:
            continue

        last = state.last_sent(s.story.key, suppress_days)
        if last is not None and s.buzz < last * escalation_factor:
            continue  # sent recently and not escalated → suppress

        survivors.append(s)
    return survivors


def select_digest(survivors: list[ScoredStory], *, max_stories: int, core_series: set[str], core_floor: int) -> list[ScoredStory]:
    """Pick the day's stories: reserve a floor of core-series slots, fill by buzz.

    `survivors` is already sorted by buzz descending. The floor is a minimum,
    not a cap — high-buzz core stories can occupy more than `core_floor` slots
    because they also compete in the general fill.
    """
    core = [s for s in survivors if s.story.series in core_series]
    guaranteed = core[:core_floor]
    guaranteed_ids = {id(s) for s in guaranteed}
    pool = [s for s in survivors if id(s) not in guaranteed_ids]
    fill = pool[: max(0, max_stories - len(guaranteed))]
    chosen = guaranteed + fill
    chosen.sort(key=lambda s: s.buzz, reverse=True)
    return chosen[:max_stories]
