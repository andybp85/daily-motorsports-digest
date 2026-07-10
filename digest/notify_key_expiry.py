"""Email reminders to rotate the Anthropic API key before it expires.

The key is created with a fixed expiration in the Anthropic console. There is no
API to read a key's own expiration, so expiry is tracked locally: an ``--init``
step records the key's SHA-256 fingerprint and the expiry date in a state file,
and a daily systemd timer runs the check below.

Reminders fire at 14, 7, and 1 days before expiry via SES (reusing the digest's
config + sender/recipient). Rotating the key cancels every pending reminder
automatically — the new value's fingerprint no longer matches, so the stale
reminders are dropped. Detecting the key value change is the fallback for not
being able to read the expiration itself.
"""
import argparse
import hashlib
import os
from dataclasses import dataclass
from datetime import date

import boto3

from digest.config import load_config
from digest.email import send_email

THRESHOLDS = (14, 7, 1)          # days before expiry to remind
_STATE_FILE = "key-expiry.state"


def _fingerprint(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@dataclass
class State:
    expires: date
    key_sha256: str
    sent: set[int]                # thresholds already emailed


def due_thresholds(today: date, expires: date, sent: set[int],
                   thresholds: tuple[int, ...] = THRESHOLDS) -> set[int]:
    """Thresholds whose reminder is due now and not yet sent.

    A threshold T becomes due once within T days of expiry (``days_left <= T``),
    so a delayed run (Pi powered off on the exact day) still catches a missed
    reminder rather than skipping it.
    """
    days_left = (expires - today).days
    return {t for t in thresholds if days_left <= t and t not in sent}


def _read_state(path: str) -> State | None:
    if not os.path.exists(path):
        return None
    data: dict[str, str] = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line and "=" in line:
                key, value = line.split("=", 1)
                data[key.strip()] = value.strip()
    return State(
        expires=date.fromisoformat(data["expires"]),
        key_sha256=data["key_sha256"],
        sent={int(x) for x in data.get("sent", "").split(",") if x},
    )


def _write_state(path: str, state: State) -> None:
    with open(path, "w") as fh:
        fh.write(f"expires={state.expires.isoformat()}\n")
        fh.write(f"key_sha256={state.key_sha256}\n")
        fh.write(f"sent={','.join(str(t) for t in sorted(state.sent))}\n")


def _send_reminder(cfg, days_left: int, state: State) -> None:
    subject = f"⚠️ Anthropic API key expires in {days_left} day(s) — rotate it"
    html = (
        f"<p>The Anthropic API key used by the motorsports digest expires on "
        f"<strong>{state.expires:%A, %B %-d, %Y}</strong> (in {days_left} day(s)).</p>"
        f"<p>Key fingerprint (sha256): <code>{state.key_sha256[:12]}…</code></p>"
        f"<p>To rotate:</p><ol>"
        f"<li>Create a new key at "
        f"<a href='https://console.anthropic.com'>console.anthropic.com</a> → API Keys.</li>"
        f"<li>Update <code>ANTHROPIC_API_KEY</code> in the Pi's <code>.env</code>.</li>"
        f"<li>Re-run the tracker: "
        f"<code>.venv/bin/python -m digest.notify_key_expiry --init --expires YYYY-MM-DD</code>.</li>"
        f"</ol>"
        f"<p>Rotating the key auto-cancels these reminders once its value changes.</p>"
    )
    ses = boto3.client("ses", region_name=cfg.aws_region)
    send_email(ses, cfg.ses_sender, cfg.ses_recipient, subject, html)


def _run(config_path: str | None, state_path: str) -> None:
    state = _read_state(state_path)
    if state is None:
        return                                   # nothing tracked, or already cancelled

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        print("[key-expiry] ANTHROPIC_API_KEY unset — cannot verify; skipping")
        return

    if _fingerprint(key) != state.key_sha256:
        os.remove(state_path)
        print("[key-expiry] key changed — reminders cancelled")
        return

    today = date.today()
    days_left = (state.expires - today).days
    due = due_thresholds(today, state.expires, state.sent)

    if due:
        _send_reminder(load_config(config_path), days_left, state)
        state.sent |= due
        _write_state(state_path, state)
        print(f"[key-expiry] reminded ({days_left} days left); sent={sorted(state.sent)}")

    # Once the final threshold has fired (or expiry has passed) there is nothing
    # left to remind about — clear tracking so future daily runs are no-ops.
    if set(THRESHOLDS) <= state.sent or days_left < 0:
        if os.path.exists(state_path):
            os.remove(state_path)
        print("[key-expiry] tracking cleared")


def _init(state_path: str, expires: str) -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY unset — cannot initialise key-expiry tracking")
    state = State(expires=date.fromisoformat(expires), key_sha256=_fingerprint(key), sent=set())
    _write_state(state_path, state)
    print(f"[key-expiry] tracking key {state.key_sha256[:12]}… expiring {expires}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Anthropic API key expiry reminders")
    parser.add_argument("--config", default=None, help="path to config.toml (for SES settings)")
    parser.add_argument("--state", default=_STATE_FILE, help="path to the tracking state file")
    parser.add_argument("--init", action="store_true",
                        help="record the current key + expiry, then exit")
    parser.add_argument("--expires", help="expiry date YYYY-MM-DD (required with --init)")
    args = parser.parse_args()

    if args.init:
        if not args.expires:
            raise SystemExit("--init requires --expires YYYY-MM-DD")
        _init(args.state, args.expires)
    else:
        _run(args.config, args.state)


if __name__ == "__main__":
    main()
