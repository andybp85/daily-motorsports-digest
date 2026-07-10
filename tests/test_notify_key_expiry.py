from datetime import date

from digest.notify_key_expiry import (
    THRESHOLDS,
    State,
    _fingerprint,
    _read_state,
    _run,
    _write_state,
    due_thresholds,
)


def test_due_thresholds_fires_only_within_window():
    expires = date(2027, 7, 10)
    # 20 days out — nothing due yet
    assert due_thresholds(date(2027, 6, 20), expires, set()) == set()
    # exactly 14 days out — the 14-day reminder is due
    assert due_thresholds(date(2027, 6, 26), expires, set()) == {14}
    # 7 days out, 14 already sent — only the 7-day reminder is due
    assert due_thresholds(date(2027, 7, 3), expires, {14}) == {7}
    # 1 day out, 14+7 sent — only the 1-day reminder is due
    assert due_thresholds(date(2027, 7, 9), expires, {14, 7}) == {1}


def test_due_thresholds_catches_up_after_a_missed_day():
    # Pi was off through the 14- and 7-day marks; a run at 5 days out still
    # owes both reminders, not just the nearest one.
    expires = date(2027, 7, 10)
    assert due_thresholds(date(2027, 7, 5), expires, set()) == {14, 7}


def test_due_thresholds_never_resends():
    expires = date(2027, 7, 10)
    assert due_thresholds(date(2027, 7, 9), expires, set(THRESHOLDS)) == set()


def test_state_round_trip(tmp_path):
    path = str(tmp_path / "key-expiry.state")
    state = State(expires=date(2027, 7, 10), key_sha256="abc123", sent={14, 7})
    _write_state(path, state)
    loaded = _read_state(path)
    assert loaded == state


def test_read_missing_state_is_none(tmp_path):
    assert _read_state(str(tmp_path / "nope.state")) is None


def test_run_cancels_when_key_changes(tmp_path, monkeypatch):
    path = str(tmp_path / "key-expiry.state")
    _write_state(path, State(expires=date(2027, 7, 10),
                             key_sha256=_fingerprint("old-key"), sent=set()))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "new-key")

    _run(config_path=None, state_path=path)     # must not touch SES/config

    assert _read_state(path) is None            # tracking cancelled


def test_run_noop_when_no_state(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "whatever")
    # No state file, no config — must return cleanly without loading either.
    _run(config_path=None, state_path=str(tmp_path / "absent.state"))
