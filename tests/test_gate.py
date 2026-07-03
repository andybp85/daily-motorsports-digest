from datetime import UTC, datetime

from digest.gate import filter_stories
from digest.models import ScoredStory, Story


def _scored(key, buzz):
    story = Story(key=key, canonical_url=f"https://x/{key}", title=key, series="f1", items=[])
    return ScoredStory(story=story, reddit_raw=0, breadth_raw=0, spike_raw=0, buzz=buzz)


class FakeState:
    def __init__(self, sent=None):
        self.sent = sent or {}          # key -> last buzz
        self.recorded = []

    def last_sent(self, key, within_days):
        return self.sent.get(key)

    def record_sent(self, key, buzz, sent_at):
        self.recorded.append((key, buzz))


def test_threshold_drops_low_scores_when_not_calibrating():
    scored = [_scored("hi", 0.8), _scored("lo", 0.2)]
    out = filter_stories(scored, FakeState(), threshold=0.5, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["hi"]


def test_calibration_ignores_threshold():
    scored = [_scored("lo", 0.1)]
    out = filter_stories(scored, FakeState(), threshold=0.9, calibration=True,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["lo"]


def test_recently_sent_story_is_suppressed():
    scored = [_scored("seen", 0.8)]
    state = FakeState(sent={"seen": 0.7})
    out = filter_stories(scored, state, threshold=0.5, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert out == []


def test_escalated_story_passes_suppression():
    scored = [_scored("seen", 0.8)]           # 0.8 > 0.5 * 1.5 = 0.75
    state = FakeState(sent={"seen": 0.5})
    out = filter_stories(scored, state, threshold=0.4, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["seen"]
