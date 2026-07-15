from digest.gate import filter_stories, select_digest
from digest.models import ScoredStory, Story, Tier


def _scored(key, buzz):
    story = Story(key=key, canonical_url=f"https://x/{key}", title=key, series="f1", items=[])
    return ScoredStory(story=story, reddit_raw=0, breadth_raw=0, spike_raw=0, buzz=buzz)


def _scored_series(key, buzz, series):
    story = Story(key=key, canonical_url=f"https://x/{key}", title=key, series=series, items=[])
    return ScoredStory(story=story, reddit_raw=0, breadth_raw=0, spike_raw=0, buzz=buzz)


class FakeState:
    def __init__(self, sent=None):
        self.sent = sent or {}  # key -> last buzz
        self.recorded = []

    def last_sent(self, key, within_days):
        return self.sent.get(key)

    def record_sent(self, key, buzz, sent_at):
        self.recorded.append((key, buzz))


def test_threshold_drops_low_scores_when_not_calibrating():
    scored = [_scored("hi", 0.8), _scored("lo", 0.2)]
    out = filter_stories(scored, FakeState(), threshold=0.5, calibration=False, suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["hi"]


def test_calibration_ignores_threshold():
    scored = [_scored("lo", 0.1)]
    out = filter_stories(scored, FakeState(), threshold=0.9, calibration=True, suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["lo"]


def test_recently_sent_story_is_suppressed():
    scored = [_scored("seen", 0.8)]
    state = FakeState(sent={"seen": 0.7})
    out = filter_stories(scored, state, threshold=0.5, calibration=False, suppress_days=3, escalation_factor=1.5)
    assert out == []


def test_escalated_story_passes_suppression():
    scored = [_scored("seen", 0.8)]  # 0.8 > 0.5 * 1.5 = 0.75
    state = FakeState(sent={"seen": 0.5})
    out = filter_stories(scored, state, threshold=0.4, calibration=False, suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["seen"]


def test_suppress_applies_even_during_calibration():
    # calibration skips only the threshold, not dedup: a recently-sent,
    # non-escalated story is still suppressed. 0.8 < 0.7 * 1.5 = 1.05.
    scored = [_scored("seen", 0.8)]
    state = FakeState(sent={"seen": 0.7})
    out = filter_stories(scored, state, threshold=0.9, calibration=True, suppress_days=3, escalation_factor=1.5)
    assert out == []


T1 = Tier(series=frozenset({"f1", "indycar"}), floor=2)


def test_select_reserves_each_tier_floor_over_higher_buzz_untiered():
    survivors = [
        _scored_series("u1", 0.9, "motogp"),  # untiered, highest buzz
        _scored_series("u2", 0.85, "motogp"),
        _scored_series("t1a", 0.3, "f1"),  # tier 1
        _scored_series("t2a", 0.2, "f2"),  # tier 2
    ]
    tiers = [Tier(frozenset({"f1", "indycar"}), 1), Tier(frozenset({"f2", "f3"}), 1)]
    out = select_digest(survivors, max_stories=3, tiers=tiers)
    keys = [s.story.key for s in out]
    assert len(out) == 3
    assert "t1a" in keys and "t2a" in keys  # both tier floors honored despite low buzz
    assert keys == ["u1", "t1a", "t2a"]  # sorted by buzz desc for display; u2 dropped


def test_select_allocates_floors_in_tier_order_when_slots_scarce():
    # Floors oversubscribe the cap (2+2 > 2). Earlier tiers win the slots;
    # a later tier's higher-buzz floor story must not evict an earlier one.
    survivors = [
        _scored_series("t1a", 0.4, "f1"),
        _scored_series("t1b", 0.3, "f1"),
        _scored_series("t2a", 0.9, "f2"),  # higher buzz but lower tier
    ]
    tiers = [Tier(frozenset({"f1"}), 2), Tier(frozenset({"f2"}), 2)]
    out = select_digest(survivors, max_stories=2, tiers=tiers)
    assert {s.story.key for s in out} == {"t1a", "t1b"}  # tier 1 claims both slots


def test_select_untiered_series_gets_no_floor_only_buzz_fill():
    survivors = [
        _scored_series("t1a", 0.9, "f1"),
        _scored_series("u1", 0.5, "motogp"),
        _scored_series("t1b", 0.1, "f1"),
    ]
    tiers = [Tier(frozenset({"f1"}), 1)]
    out = select_digest(survivors, max_stories=2, tiers=tiers)
    # floor takes t1a; remaining slot fills by buzz -> u1 beats t1b
    assert [s.story.key for s in out] == ["t1a", "u1"]


def test_select_underfilled_tier_floor_wastes_no_slot():
    survivors = [
        _scored_series("u1", 0.9, "nascar"),
        _scored_series("u2", 0.8, "wec"),
        _scored_series("t1", 0.5, "f1"),
    ]
    tiers = [Tier(frozenset({"f1", "indycar"}), 2)]  # floor 2, but only 1 tier story exists
    out = select_digest(survivors, max_stories=3, tiers=tiers)
    assert [s.story.key for s in out] == ["u1", "u2", "t1"]  # unused floor slot fills by buzz


def test_select_high_buzz_tier_may_exceed_its_floor():
    survivors = [
        _scored_series("a", 0.9, "f1"),
        _scored_series("b", 0.85, "f1"),
        _scored_series("c", 0.8, "f1"),
        _scored_series("u", 0.7, "nascar"),
    ]
    tiers = [Tier(frozenset({"f1"}), 1)]
    out = select_digest(survivors, max_stories=3, tiers=tiers)
    assert [s.story.key for s in out] == ["a", "b", "c"]  # floor is a minimum, not a cap


def test_select_caps_at_max_stories():
    survivors = [_scored_series(f"s{i}", 1.0 - i / 100, "f1") for i in range(20)]
    tiers = [Tier(frozenset({"f1"}), 6)]
    out = select_digest(survivors, max_stories=15, tiers=tiers)
    assert [s.story.key for s in out] == [f"s{i}" for i in range(15)]
    assert [s.buzz for s in out] == sorted((s.buzz for s in out), reverse=True)
