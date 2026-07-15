from typing import Protocol

from digest.models import ScoredStory, Tier


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


def select_digest(survivors: list[ScoredStory], *, max_stories: int, tiers: list[Tier]) -> list[ScoredStory]:
    """Pick the day's stories: reserve each tier's floor in order, fill by buzz.

    `survivors` is already sorted by buzz descending. Floors are minimums, not
    caps — a high-buzz tier can occupy more than its floor because its extra
    stories also compete in the general fill. Floors are honored in tier order,
    so when slots are scarce an earlier tier is never evicted by a later one.
    """
    chosen: list[ScoredStory] = []
    chosen_ids: set[int] = set()
    for tier in tiers:
        room = max_stories - len(chosen)
        if room <= 0:
            break
        picks = [s for s in survivors if s.story.series in tier.series and id(s) not in chosen_ids][: min(tier.floor, room)]
        chosen.extend(picks)
        chosen_ids.update(id(s) for s in picks)

    room = max_stories - len(chosen)
    if room > 0:
        chosen.extend([s for s in survivors if id(s) not in chosen_ids][:room])  # buzz-ordered fill

    chosen.sort(key=lambda s: s.buzz, reverse=True)
    return chosen
