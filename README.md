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

3. **Reddit app:** register a *script*-type app at
   <https://www.reddit.com/prefs/apps> to get `REDDIT_CLIENT_ID` /
   `REDDIT_CLIENT_SECRET`. Free tier (100 QPM) is fine for personal use.

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

## Tests

```bash
.venv/bin/python -m pytest -v
```
