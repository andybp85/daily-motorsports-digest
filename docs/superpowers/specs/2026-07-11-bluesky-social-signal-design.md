# Bluesky social-engagement signal — design

**Date:** 2026-07-11
**Bean:** `daily-motorsports-digest-qzme` (feature) · related finding `daily-motorsports-digest-pxca`
**Status:** approved design, pre-implementation

## Problem

The digest scores stories by three rank-normalized signals — `reddit` (weight
0.5), `breadth` (0.35), `spike` (0.15) — summed into `buzz`. In practice all
three are flat, so ranking does nothing:

- **`reddit` is dead.** Reddit is disabled (Responsible Builder Policy), so
  `reddit_raw = 0` for every story; `rank_normalize` ties them at 0.5. The
  dominant signal contributes a constant.
- **`breadth` barely varies.** `cluster_items` merges items only on exact URL or
  fuzzy title `token_sort_ratio >= 88`. Different outlets rephrase headlines, so
  cross-outlet merges almost never happen — every story is a singleton, so
  `breadth = 1` for all (measured 18/18 on a real pool; prod dry-run top-8 all
  "1 outlets").
- **`spike` is series-coarse.** The GDELT per-series ratio varies only *between*
  series (all F1 share one value, all IndyCar another) and is often neutral or
  failed. It cannot rank stories *within* a series.

Net: within a series the digest order is essentially the stable-sort input
order. Reweighting is a measured no-op (all candidate weightings → 1 distinct
score) because no underlying signal varies.

## Goal

Restore a real **per-story** community-engagement signal by measuring how much a
story's article is being shared and engaged with on Bluesky. This is the
highest-leverage ranking fix available and, unlike Reddit, Bluesky's API is
reachable with a free app password (no manual-approval gate).

Scope note (from live probe, 2026-07-11): F1 has real daily volume on Bluesky
(~1000+ relevant posts, ~53% carrying external article links); **IndyCar is
effectively absent** (Palou 1, Newgarden 1, O'Ward 3 posts/day). So this revives
the F1 half of the community signal; IndyCar stories will typically score 0
(neutral within the pool). That is acceptable — 0 is neutral, not penalizing.

## Non-goals

- Ranking IndyCar by Bluesky (no volume there).
- Per-entity "who's being talked about" buzz as the primary signal — the live
  probe showed bare-surname queries are dominated by off-topic noise (Bertrand
  Russell, Chuck Norris, the 1966 *Grand Prix* film). Kept only as a fallback.
- Reweighting `buzz`. Out of scope until a per-story signal exists; revisit after.

## Approach: post-cluster enrichment (model A)

### Why enrichment, not a collector

Reddit/GDELT are **pre-cluster collectors**: they add `RawItem`s, then
clustering groups them. Model A cannot work that way — to find posts linking a
story we need its `canonical_url`, which exists only *after* clustering. And
fetching Bluesky posts by keyword and letting clustering absorb them (model B)
misattributes engagement: freeform post text won't fuzzy-match article headlines,
and surname noise pollutes the count.

Therefore Bluesky runs as an **enrichment stage between clustering and scoring**:

```
normalize → cluster → [bluesky enrich] → score
```

`pipeline.score_pool` currently does `normalize → cluster → score` internally.
Add an optional `enrich` seam: `score_pool(raw, spikes, cfg, enrich=None)`, where
`enrich` is a `list[Story] -> list[Story]` callable applied between `cluster_items`
and `score_stories` (identity when `None`). `main.run` passes
`enrich=lambda stories: bluesky.enrich(stories, client, cfg)`. This keeps
clustering inside the pipeline, keeps the Bluesky specifics in `main`, and makes
the seam trivially testable with a stub callable.

### Matching a story to posts

For each clustered `Story`, find posts linking its article via up to two search
calls, **short-circuited** to keep runs fast:

1. **Direct URL search** — `searchPosts q=<canonical_url>`; catches posts with
   the raw link in text. If this yields matches, stop.
2. **Title-terms + embed match** (only if pass 1 found nothing) — `searchPosts
   q=<top title words>, sort=top`, then keep posts whose `record.embed` is
   `app.bsky.embed.external*` and whose `external.uri` **normalizes-equal** to the
   story's `canonical_url`.

So most stories cost one search call, worst case two. URL normalization:
lowercase, strip scheme + `www.`, strip query and fragment, strip trailing slash.
Dedupe matched posts by URI (a post can appear in both passes).

Story social score = Σ over matched posts of `likeCount + repostCount +
replyCount`.

### Fallback (guarded per-entity)

If the feasibility gate (below) shows URL-matching is too sparse — few Bluesky
users link the digest's outlets (autosport, the-race, motorsport.com, racer) —
switch the enrichment to: `searchPosts` on the story's series/driver keywords,
run every candidate post's text through the existing `normalize.is_relevant()`
gate to strip noise, then sum engagement. Coarser and noisier, but salvages a
signal. Same enrichment seam; only the matching function changes.

### Feeding the score (repurpose `reddit → social`)

No change to the scoring math. The enrichment appends **one synthetic item** per
story carrying the aggregated engagement:

```python
RawItem(source="bluesky", url=story.canonical_url, title=story.title,
        reddit_score=likes + reposts, reddit_comments=replies, series=story.series)
```

Rename the signal end-to-end `reddit → social`:

- `config.toml`: `[weights] reddit` → `social` (same 0.5 value).
- `score.py`: `_reddit_signal` → `_social_signal` (unchanged body: it already
  sums `reddit_score + reddit_comments` over items, so the synthetic item is
  picked up automatically), and `weights["reddit"]` → `weights["social"]`.
- If Reddit is ever re-enabled, its items sum into the same `social` signal.

`ScoredStory.reddit_raw` and `RawItem.reddit_score/reddit_comments` field names
stay as-is for this iteration (renaming the data fields is a wider churn with no
functional gain); only the *signal/weight* is renamed. This is a deliberate,
documented asymmetry.

## Components

| Unit | Responsibility | Depends on | Tested |
|---|---|---|---|
| `collect/bluesky.py: normalize_url(u)` | canonical URL comparison form | — | unit |
| `collect/bluesky.py: external_uri(post)` | pull embed article URI, or "" | — | unit |
| `collect/bluesky.py: match_posts(story, posts)` | posts whose embed == story URL | normalize_url, external_uri | unit |
| `collect/bluesky.py: engagement(posts)` | Σ like+repost+reply | — | unit |
| `collect/bluesky.py: BlueskyClient` | thin I/O: `createSession`, `search_posts` | urllib | injected fake |
| `collect/bluesky.py: enrich(stories, client, cfg)` | attach synthetic social item per story | the helpers above | unit w/ fake client |
| `config.py` | load `BSKY_HANDLE`/`BSKY_APP_PASSWORD`, `bluesky_enabled` | env, toml | unit |
| `pipeline.py` | expose cluster step; call enrich between cluster and score | enrich | unit |

`BlueskyClient` is injectable (`enrich(stories, client=None, ...)`), mirroring
`fetch_gdelt(client=None)`, so all logic is testable without network.

## Data flow

```
main.run
  raw, spikes = _collect(cfg)                 # RSS + GDELT (+Reddit if ever enabled)
  enrich = lambda stories: bluesky.enrich(stories, client, cfg)   # NEW
  scored = score_pool(raw, spikes, cfg, enrich=enrich)
  ...gate, summarize, send...

pipeline.score_pool(raw, spikes, cfg, enrich=None)
  normalized = normalize_items(raw)
  stories    = cluster_items(normalized)
  stories    = enrich(stories) if enrich else stories   # appends social items
  return score_stories(stories, spikes, cfg.weights)
```

`enrich` opens one session, then 1–2 search calls per story (short-circuited;
the pool is tens of stories). Queries both series; IndyCar simply yields ~0
matches.

## Error handling & config

Mirror the Reddit/GDELT degradation pattern exactly:

- `config.toml`: `bluesky_enabled = false` default; enable explicitly.
- `.env`: `BSKY_HANDLE`, `BSKY_APP_PASSWORD` (git-ignored; loaded by systemd
  `EnvironmentFile` on the server, same as the Anthropic/AWS creds).
- Disabled or missing creds → `print("[bluesky] disabled / no creds — skipping")`,
  return stories unchanged.
- `createSession` failure → `[bluesky] auth failed: … — skipping`, stories
  unchanged.
- Per-story search failure → log, treat as 0 matches, continue (one story must
  not kill the run).
- Each `search_posts` HTTP call bounded by a timeout (reuse the SIGALRM
  `_time_limit` pattern from `collect/gdelt.py`, or pass `urllib` a timeout) so a
  stalled Bluesky endpoint can't hang the digest — the same failure mode we just
  fixed for GDELT.

## Testing

- Pure helpers (`normalize_url`, `external_uri`, `match_posts`, `engagement`)
  with fixture post JSON — no network.
- `enrich` with a fake `BlueskyClient` returning canned search results: asserts
  the right synthetic item is appended, engagement summed, unmatched stories left
  untouched, and disabled/failure paths return stories unchanged.
- `score.py` rename covered by existing score tests updated to `social` weight
  key.
- No live-network tests in the suite.

## Implementation gate (first step)

Before building model A, with a **fresh** Bluesky app password, run the match
probe against a day of real story URLs:

- **Go** — URL-matching yields non-trivial matched posts/engagement on several F1
  stories → implement model A as specified.
- **Thin** — implement the guarded per-entity fallback instead; rest of the
  design (enrichment seam, scoring, config, tests) is unchanged.

Log whatever is decided so the choice is auditable.

## Security note

The app password used for the 2026-07-11 probes was shared in plaintext and has
been revoked. The real integration uses a fresh app password stored only in
`.env` (git-ignored) — never committed, never written to a bean.
