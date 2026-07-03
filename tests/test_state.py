from datetime import UTC, datetime, timedelta

from digest.state import StateStore


def test_unseen_key_returns_none(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    assert store.last_sent("k1", within_days=3) is None
    store.close()


def test_recorded_key_within_window_returns_buzz(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    now = datetime.now(UTC)
    store.record_sent("k1", 0.7, now)
    assert store.last_sent("k1", within_days=3) == 0.7
    store.close()


def test_key_outside_window_returns_none(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    old = datetime.now(UTC) - timedelta(days=5)
    store.record_sent("k1", 0.7, old)
    assert store.last_sent("k1", within_days=3) is None
    store.close()


def test_last_sent_returns_most_recent_score(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    now = datetime.now(UTC)
    store.record_sent("k1", 0.4, now - timedelta(days=2))
    store.record_sent("k1", 0.9, now)
    assert store.last_sent("k1", within_days=3) == 0.9
    store.close()
