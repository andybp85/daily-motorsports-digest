from digest.config import Config
from digest.models import RawItem
from digest.pipeline import rank


class FakeState:
    def last_sent(self, key, within_days):
        return None

    def record_sent(self, *a):
        pass


def _cfg():
    return Config(
        calibration=True, suppress_days=3, escalation_factor=1.5,
        weights={"reddit": 0.5, "breadth": 0.35, "spike": 0.15},
        keywords={"series_f1": ["F1", "Grand Prix"], "series_indycar": ["IndyCar"],
                  "teams": [], "drivers": [], "anchors": []},
    )


def test_rank_normalizes_clusters_scores_and_orders():
    raw = [
        RawItem(source="rss", url="https://autosport.com/a?utm_source=x",
                title="Verstappen to Mercedes rumor resurfaces", series="f1"),
        RawItem(source="rss", url="https://motorsport.com/b",
                title="Verstappen to Mercedes rumour resurfaces", series="f1"),
        RawItem(source="reddit", url="https://autosport.com/a",
                title="Verstappen to Mercedes rumor resurfaces", series="f1",
                reddit_score=5000, reddit_comments=900),
        RawItem(source="rss", url="https://racer.com/c",
                title="Iowa doubleheader preview", series="indycar"),
    ]
    scored = rank(raw, {"f1": 2.0, "indycar": 1.0}, FakeState(), _cfg())

    # The three Verstappen items collapse to one story; two stories total.
    assert len(scored) == 2
    assert scored[0].story.title.startswith("Verstappen")     # highest buzz first
    assert scored[0].breadth_raw >= 2                          # merged across domains


def test_rank_gate_suppresses_recently_sent():
    class SuppressState:
        def last_sent(self, key, within_days):
            return 1.0        # already sent high; nothing escalates past 1.0 * 1.5
        def record_sent(self, *a):
            pass

    raw = [RawItem(source="rss", url="https://a/x", title="F1 news", series="f1")]
    cfg = _cfg()
    cfg.calibration = False
    cfg.threshold = 0.0
    scored = rank(raw, {"f1": 1.0}, SuppressState(), cfg)
    assert scored == []
