# F1/IndyCar Morning Buzz Digest — Design Spec

**Date:** 2026-07-03
**Status:** Approved, ready for implementation plan

## Goal

A daily cron job on a Raspberry Pi that emails a morning recap of F1/IndyCar
news from the previous day, ranked by engagement/buzz — including stories from
outlets the user doesn't normally read. Sends via existing Amazon SES setup.
No email on genuinely slow news days.

## Decisions locked in brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| Summary source | Titles + GDELT metadata + Reddit discussion. **No article scraping.** | Robust, paywall-proof, zero fetch failures. GDELT/Reddit return metadata, not article bodies; summarizing from that + discussion is honest and reliable. |
| Summarizer model | Haiku 4.5 (`claude-haiku-4-5`) | Cheapest current Claude model ($1/$5 per MTok). One call/day → negligible cost. Note: Haiku 4.5 does not support the `effort` param or adaptive thinking; a summarization call needs neither. |
| Email format | Short blurb per story (5–8), ranked by buzz, ungrouped | Scannable but substantive; biggest story leads regardless of series. |
| Discovery keyword scope | Series + teams + drivers (max recall) | Catches driver-personal stories. Noise mitigated by co-term requirement + multi-signal scoring (below). |
| Cron target | Raspberry Pi | Known-good Python toolchain; NAS TeraStation firmware is locked-down with ancient Python. |
| Scheduler | systemd timer | Better logging/failure visibility than cron. |
| Suppress window | 3 days, with escalation re-send | Prevents repeating a still-hot story every morning; allows a genuinely developing story to resurface. |
| Score weights | Reddit 0.5 / breadth 0.35 / spike 0.15 | Reddit is the sharpest buzz signal; user asked for buzz. Tunable in config. |
| Threshold | Calibration period (~2 weeks) before enforcing | Off-weekends and off-season mean many genuinely quiet days; the threshold must be set from real score distribution, not guessed. |

## Data sources

Three independent layers, each covering "outlets I don't read" from a different angle:

- **RSS** — reliability floor from known-good sources: Autosport, The Race,
  Motorsport.com, RACER (IndyCar). Via `feedparser`.
- **GDELT DOC 2.0 API** — discovery layer. Free, no API key, updates every
  15 min, scans 50,000+ outlets. Query past 24h for F1/IndyCar keywords.
  Endpoint `https://api.gdeltproject.org/api/v2/doc/doc`, via the `gdeltdoc`
  Python client. Provides url/title/seendate/domain/tone plus a timeline/volume
  mode (the coverage-spike signal).
- **Reddit** — engagement layer. Via `praw` against r/formula1 and r/IndyCar,
  top/hot posts from the past 24h. Score + comment count = the buzz signal.
  Also surfaces crossposts and community sentiment. Free tier (100 QPM, OAuth,
  script-type app) is explicitly fine for personal use.

X/Twitter is deliberately excluded: no free read tier since Feb 2023, and
pay-per-read economics ($0.005/read) don't justify it for this use case.

## Pipeline

Seven stages, run once daily at ~06:00 local. Each stage is a pure function of
the previous stage's output where possible — unit-testable, and stages 1–5 can
dry-run to a ranked list without sending anything.

```
1. collect    RSS + GDELT + Reddit         →  raw items
2. normalize  canonicalize URLs, extract    →  normalized items
              domain/title/timestamps
3. cluster    group raw items into stories  →  story clusters
4. score      per-signal normalize →         →  scored stories
              combined buzz score
5. gate       drop below-threshold +          →  surviving stories
              already-sent stories
6. summarize  Haiku writes a blurb per        →  blurbs
              surviving story (top 5–8)
7. send       render HTML → SES →             →  email sent
              record sent stories in state
```

### Stage 1 — collect

One module per source under `collect/`. Each returns a list of raw items with a
common shape: `{source, url, title, domain, published_at, engagement?, extra}`.
All three run every day; failures in one source are logged and degrade
gracefully (a dead GDELT request doesn't kill the Reddit layer).

**Time window:** past 24h in UTC, computed once at run start. Reddit uses
`top(time_filter='day')`. GDELT uses a 24h timespan. RSS entries are filtered by
`published_at`.

### Stage 2 — normalize

- **URL canonicalization:** strip tracking params (`utm_*`, `fbclid`, `gclid`,
  etc.), normalize AMP URLs → canonical, drop fragments, lowercase host, strip
  trailing slash.
- Extract domain, clean title, parse timestamps to UTC.

### Stage 3 — cluster (dedup)

Group normalized items into **stories**. A story is a cluster of items that
refer to the same event across sources (the Autosport version, the
Motorsport.com syndication, the Reddit crosspost linking one of them).

- Cluster by canonical-URL match **OR** fuzzy title match
  (`rapidfuzz` token-sort ratio ≥ 88).
- **Cluster size across distinct domains = the coverage-breadth buzz signal.**
  Clustering and scoring share this concern by design.

### Stage 4 — score

Three raw signals per story:

1. **Reddit engagement** — combined score + comment count across the cluster's
   Reddit items.
2. **Coverage breadth** — count of distinct domains in the cluster.
3. **Coverage spike** — GDELT timeline/volume signal (tone/volume anomaly).

Signals live on different scales, so **rank-normalize each within the day's
pool** to 0–1, then weighted sum:

```
buzz = 0.5 * reddit_rank + 0.35 * breadth_rank + 0.15 * spike_rank
```

Rank-normalize (not z-score) because the daily pool is small and often skewed.
Weights are config values.

**Driver-name noise mitigation:** the full driver list maximizes recall but
common surnames ("Russell", "Palou", "Norris") match unrelated news. Two
defenses: (a) in the GDELT query, require each driver name to co-occur with a
motorsport anchor term, e.g. `"Palou" (IndyCar OR "Indy 500" OR racing)`;
(b) the multi-signal score naturally suppresses a lone false positive — a
mis-hit with no Reddit traction and no coverage breadth won't clear the gate.

### Stage 5 — gate

Two filters against a SQLite state store:

- **Threshold gate:** drop stories with `buzz` below the configured threshold.
  When `calibration = true`, this gate is **skipped** — send every day and log
  the day's score distribution (see Calibration below).
- **Already-sent gate:** drop stories whose key (canonical URL + title hash) was
  sent within the **suppress window (3 days)** — *unless* the story's current
  buzz score exceeds its last-sent score by the **escalation factor**
  (config, default `1.5×`), in which case it passes as a genuinely developing
  story. The last-sent score is read from the state store.

If nothing survives the gate (and not in calibration mode), **no email is sent**
that day. This is logged with the top score so a skipped day is distinguishable
from a failure.

### Stage 6 — summarize

Top 5–8 surviving stories go to Haiku 4.5 in a single API call. Input per
story: headline(s), source domains, coverage breadth, Reddit score/comment
count, and top Reddit comment snippets. Output: a 2–3 sentence blurb per story.

Model: `claude-haiku-4-5`. No `thinking`, no `effort` (unsupported on Haiku and
unneeded). `max_tokens` sized for ~8 blurbs.

### Stage 7 — send

- Render an HTML email: ranked blurbs, each with headline, blurb, source link,
  and a buzz signal line (e.g. "4.2k upvotes · 42 outlets").
- Send via `boto3` SES.
- On successful send, record each sent story's key + buzz score + timestamp in
  the SQLite state store (feeds the suppress window and escalation check).

## Calibration

Ships with `calibration = true`. For the first ~2 weeks:

- The threshold gate is skipped — an email is sent every day regardless of
  score.
- The day's score distribution is logged.

After ~2 weeks, set the threshold from the observed distribution, flip
`calibration = false`, and the "no slow-news-day emails" behavior activates.
The suppress window may also be re-tuned from observed behavior during this
period.

## State store (SQLite)

Single-file SQLite DB on the Pi. One table of sent stories:

| column | purpose |
|---|---|
| `story_key` | canonical URL + title hash (dedup identity) |
| `buzz_score` | score at time of send (for escalation comparison) |
| `sent_at` | timestamp (for suppress-window expiry) |

Queried in stage 5 (already-sent gate + escalation), written in stage 7.

## Stack & layout

- **Python 3.11+**
- **Dependencies (each justified by present need):**
  - `praw` — Reddit API
  - `gdeltdoc` — GDELT DOC 2.0 client
  - `feedparser` — RSS
  - `rapidfuzz` — fuzzy title clustering
  - `boto3` — SES
  - `anthropic` — Haiku summarization
- **Config** (`.toml` or env, 12-factor): Reddit creds, AWS/SES, Anthropic key,
  score weights, threshold, `calibration` flag, suppress window, escalation
  factor, keyword lists (series, teams, drivers).
- **Secrets** via env / git-ignored `.env`. Never committed.
- **Module layout** — small, single-purpose files:
  ```
  collect/
    rss.py
    gdelt.py
    reddit.py
  normalize.py
  cluster.py
  score.py
  state.py        # SQLite
  summarize.py
  email.py
  main.py         # orchestrator
  config.py
  ```
- **Deployment:** Raspberry Pi, systemd timer firing `main.py` at ~06:00 local.

## Testing

- Each stage is independently unit-testable (pure functions over the prior
  stage's output).
- Stages 1–5 produce a ranked list — a `--dry-run` mode prints the ranked
  stories without summarizing or sending.
- Clustering, canonicalization, and scoring get focused unit tests with fixture
  data (syndicated-story fixtures, tracking-param URLs, driver-name false
  positives).

## Out of scope (YAGNI)

- Article body scraping / full-text fetch.
- X/Twitter integration.
- NewsAPI.org (GDELT covers discovery better, for free).
- Web UI / dashboard — email is the only output surface.
- Multi-user / configurable recipients beyond the single user.
