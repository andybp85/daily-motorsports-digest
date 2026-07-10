---
# daily-motorsports-digest-3ixj
title: Anthropic key-expiry email reminders (14/7/1 days), self-cancel on key change
status: completed
type: feature
priority: normal
created_at: 2026-07-10T11:45:41Z
updated_at: 2026-07-10T11:49:56Z
---

Anthropic API key created 2026-07-10 with 365-day expiry (2027-07-10). Send SES email reminders 14, 7, and 1 days before expiry. Cancel pending reminders automatically if the key changes (Anthropic has no API to read a key's own expiration, so track the key's sha256 fingerprint locally and detect value change). Pi systemd daily timer + Python module reusing config + SES.

## Summary of Changes

- `digest/notify_key_expiry.py` — daily check + `--init` recorder. Pure `due_thresholds()` (fires within-window, catches up after a missed day, never resends). State = expiry date + key sha256 + sent thresholds, in `key-expiry.state` (key=value). Reminds via SES (reuses `digest.config.load_config` + `digest.email.send_email`). Self-cancels: daily run sees a changed fingerprint → removes state; also clears state once all thresholds sent or expiry passed.
- `tests/test_notify_key_expiry.py` — 7 tests (window logic, catch-up, no-resend, state round-trip, cancel-on-key-change, no-op-without-state). Full suite 64 passed.
- `deploy/key-expiry-notify.{service,timer}` — oneshot + daily `OnCalendar 07:30`, `Persistent=true`.
- `deploy/install.sh` — installs all four units, enables both timers, prints the one-time `--init` command.
- `.gitignore` — `key-expiry.state`. README — deploy subsection documenting the `--init --expires` step.

One-time on the Pi: `--init --expires 2027-07-10` (verify the date against the console).
