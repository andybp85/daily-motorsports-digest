# Daily Motorsports Digest

A daily job that emails a buzz-ranked recap of motorsports news, sourced from
RSS + GDELT + Reddit, summarized by Claude Haiku 4.5, and sent via Amazon SES.
No email on genuinely slow news days. The followed series are configurable
(ships with F1, IndyCar, WEC, IMSA, NASCAR, and Formula E) — see
[Series configuration](#series-configuration).

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

   Fill in SES sender/recipient, the followed-series registry, and (in
   `.env`) Reddit + Anthropic + AWS credentials. `.env` and `config.toml` are
   git-ignored. See [Series configuration](#series-configuration) for the
   `[[series]]` block.

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

## Series configuration

Followed series live in `config.toml` as a registry: one `[[series]]` block
per series, in priority order. There is no hardcoded keyword list in code —
the registry *is* the relevance filter.

```toml
[[series]]
id = "f1"
label = "Formula 1"
terms = ["Formula 1", "Formula One", "F1", "Grand Prix",
         "Verstappen", "Lewis Hamilton", "Lando Norris", "Red Bull Racing"]

[[series]]
id = "indycar"
label = "IndyCar"
terms = ["IndyCar", "Indy 500", "Palou", "Newgarden", "Scott Dixon"]
```

- **`id`** — lowercase slug, used internally (e.g. as a `[[tier]]` member or
  a feed's forced `series` value).
- **`label`** — display name shown in the digest.
- **`terms`** — list of distinctive title strings. A story is kept only if its
  title matches (case-insensitive substring) a term from some series in the
  registry; otherwise it's dropped as irrelevant. **Registry order is match
  priority** — the first series whose term matches wins, so put more specific
  series before more general ones when a title could plausibly match both.

**Terms must be unambiguous outside motorsport.** The `f1` and `indycar` terms
are also the keywords sent to GDELT, which indexes general world news, and the
relevance filter then re-checks that same list — so an ambiguous term is both
what pulls a story in and what waves it through, and nothing downstream catches
it. Bare `Hamilton` once filled a digest with Hamilton, Ontario city politics
and Hamilton Insurance Group earnings. Name drivers in full (`Lewis Hamilton`),
and avoid teams that run entries in several series (`Penske`, `Ganassi`).

See `config.example.toml` for the full registry shipped by default: the F1
feeder ladders (F2, F3, F1 Academy) and Indy NXT lead the list — listed
before their parent series so a specific hit (e.g. "F1 Academy") wins over the
parent's broader terms ("F1") — then F1, IndyCar, WEC, IMSA, NASCAR, Formula E.

### Selection: `max_stories` and `[[tier]]`

```toml
max_stories = 15

[[tier]]                                              # 1st priority
series = ["f1", "indycar"]
floor = 6
[[tier]]                                              # 2nd — feeder ladders
series = ["f2", "f3", "f1academy", "indynxt"]
floor = 3
[[tier]]                                              # 3rd
series = ["wec", "formulae"]
floor = 2
[[tier]]                                              # 4th
series = ["nascar", "imsa"]
floor = 2
```

- **`max_stories`** — the maximum number of stories in a digest.
- **`[[tier]]`** — priority bands, applied top-down. Each reserves a floor of
  up to `floor` slots for the highest-buzz stories from its `series` IDs; once
  every tier has its floor, the remaining slots fill by buzz across *all*
  followed series, capped at `max_stories`. A floor is a **minimum**, not a
  cap — a tier buzzy enough to fill more than its floor still can. When slots
  are scarce, floors are honored in tier order, so an earlier tier is never
  evicted by a later one. Summed floors must be `<= max_stories` (validated at
  load). A series named in **no** tier has floor 0 — it competes only in the
  buzz fill. If no `[[tier]]` is declared, selection defaults to a single
  F1/IndyCar tier with floor 6.

### GDELT spike coverage

GDELT's spike signal (`[weights].spike`) is scoped to F1 and IndyCar only.
Other series (WEC, IMSA, NASCAR, Formula E, and any you add) rank on the
social and breadth signals alone — spike defaults to a neutral `1.0` for
them, so it neither helps nor hurts their ranking.

### How to add a new series

No code change is required:

1. Add a `[[series]]` block to `config.toml` with a unique `id`, a display
   `label`, and distinctive `terms`: the series name, signature events (e.g.
   a marquee race), and unambiguous driver/team names. **Avoid bare shared
   manufacturer names** like "Ferrari" or "Porsche" — those manufacturers
   race across multiple series, and a bare name causes cross-series leakage
   (a story about one series' Ferrari program getting misclassified into
   another's digest).
2. Optionally add a feed (`[[rss_feeds]]` or `[[subreddits]]`) with
   `series = "<id>"` to force-classify every entry from a dedicated source
   into that series, bypassing title matching for that source.
3. If the new series should share in a guaranteed floor, add its `id` to a
   `[[tier]]` (or a new tier at the priority you want). Untiered series still
   appear — they just compete on buzz alone with no reserved floor.

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

To inspect runs afterwards, see [Logs](#logs).

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

## Logs

The digest writes no log file. On the Pi it runs under systemd, so everything it
prints goes to journald:

```bash
journalctl -u motorsports-digest.service -n 50          # last 50 lines
journalctl -u motorsports-digest.service -f             # follow live
journalctl -u motorsports-digest.service --since today  # today's run only
systemctl status motorsports-digest.timer               # last/next run
```

Swap in `key-expiry-notify.service` for the API key-expiry reminder logs.

Run it by hand instead and the same output goes straight to stdout — this is
where the `[calibration]` score lines show up:

```bash
.venv/bin/python -m digest.main --dry-run
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
