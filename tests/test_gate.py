from digest.gate import filter_stories, select_digest
from digest.models import ScoredStory, Story


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


CORE = {"f1", "indycar"}


def test_select_reserves_floor_for_core_over_higher_buzz_others():
    survivors = [
        _scored_series("o1", 0.9, "nascar"),
        _scored_series("o2", 0.8, "wec"),
        _scored_series("c1", 0.3, "f1"),
        _scored_series("c2", 0.2, "indycar"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=2)
    keys = [s.story.key for s in out]
    assert len(out) == 3
    assert "c1" in keys and "c2" in keys  # floor honored despite low buzz
    assert keys == ["o1", "c1", "c2"]  # sorted by buzz desc for display


def test_select_underfilled_floor_wastes_no_slot():
    survivors = [
        _scored_series("o1", 0.9, "nascar"),
        _scored_series("o2", 0.8, "wec"),
        _scored_series("c1", 0.5, "f1"),
        _scored_series("o3", 0.4, "imsa"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=2)
    assert [s.story.key for s in out] == ["o1", "o2", "c1"]  # only 1 core exists; fill by buzz


def test_select_high_buzz_core_may_exceed_floor():
    survivors = [
        _scored_series("c1", 0.9, "f1"),
        _scored_series("c2", 0.85, "indycar"),
        _scored_series("c3", 0.8, "f1"),
        _scored_series("o1", 0.7, "nascar"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=1)
    assert [s.story.key for s in out] == ["c1", "c2", "c3"]  # floor is a minimum, not a cap


def test_select_caps_at_max_stories():
    survivors = [_scored_series(f"s{i}", 1.0 - i / 100, "nascar") for i in range(20)]
    out = select_digest(survivors, max_stories=15, core_series=CORE, core_floor=6)
    assert len(out) == 15
