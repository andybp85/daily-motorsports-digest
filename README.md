# Daily Motorsports Digest

A daily job that emails a buzz-ranked recap of F1/IndyCar news, sourced from
RSS + GDELT + Reddit, summarized by Claude Haiku 4.5, and sent via Amazon SES.
No email on genuinely slow news days.

See `docs/superpowers/specs/2026-07-03-motorsports-digest-design.md` for the
full design.

## Setup

1. **Python 3.11+.** Create a venv and install deps:

   ```bash
   python3.11 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```

2. **Config:** copy and edit the templates:

   ```bash
   cp config.example.toml config.toml
   cp .env.example .env
   ```

   Fill in SES sender/recipient, keyword lists, and (in `.env`) Reddit +
   Anthropic + AWS credentials. `.env` and `config.toml` are git-ignored.

3. **Reddit (optional):** Reddit is one ranking signal, not required. As of late
   2025 Reddit's [Responsible Builder Policy][rbp] gates new API tokens behind
   manual approval, so self-serve script-app creation at
   <https://www.reddit.com/prefs/apps> may dead-end in a captcha loop. To run
   without Reddit, set `reddit_enabled = false` in `config.toml` (or just leave
   the `REDDIT_*` env vars unset — it skips automatically). To pursue access, see
   [docs/reddit-api-access-request.md](docs/reddit-api-access-request.md). If you
   already have working creds, set `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`.

[rbp]: https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy

4. **SES:** verify the sender (and, in sandbox mode, the recipient) address in
   the AWS SES console for your region.

## Run

```bash
# Rank and print the day's stories without summarizing or sending:
.venv/bin/python -m digest.main --dry-run

# Full run (summarize + email):
.venv/bin/python -m digest.main
```

## Calibration

Ships with `calibration = true` in `config.toml`. For the first ~2 weeks it
sends every day regardless of score and logs the day's buzz distribution. Watch
the `[calibration]` log lines, then pick a `threshold` from the observed scores,
set `calibration = false`, and the "no slow-news-day emails" behavior activates.

## Deploy on a Raspberry Pi (systemd timer)

The unit files are templates (`__DIR__` / `__USER__` placeholders); the install
script fills them in for this machine — no hand-editing:

```bash
sudo ./deploy/install.sh
```

By default it runs as the invoking user with `DIR` set to this checkout.
Override either:

```bash
SERVICE_USER=digest SERVICE_DIR=/opt/digest sudo -E ./deploy/install.sh
```

Inspect runs with:

```bash
systemctl status motorsports-digest.timer
journalctl -u motorsports-digest.service -n 50
```

### API key-expiry reminders

`install.sh` also installs a second daily timer (`key-expiry-notify.timer`) that
emails you at 14, 7, and 1 days before the Anthropic API key expires. Anthropic
has no API to read a key's own expiry, so it's tracked locally: run this once
after deploy (and again each time you rotate the key), passing the expiry shown
in the console:

```bash
.venv/bin/python -m digest.notify_key_expiry \
  --config config.toml --state key-expiry.state \
  --init --expires 2027-07-10
```

The tracker fingerprints the key (sha256, never stored in plaintext). Rotating
the key auto-cancels any pending reminders — the daily check sees the value
changed and drops the stale state file. `key-expiry.state` is gitignored.

## Tests

```bash
.venv/bin/python -m pytest -v
```

## Issue tracking (beans)

Follow-up work lives in the committed `.beans/` store (plaintext markdown, one
file per issue). Because beans are committed, a `pre-commit` hook scans staged
`.beans/**` and blocks any commit that would leak personal info or secrets.

That hook lives in `.git/hooks/` (untracked, so it never gets committed), which
means it does **not** survive a clone. Re-arm it in each fresh checkout:

```bash
bash ~/.claude/skills/pii-commit-guard/install.sh
```
