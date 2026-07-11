---
# daily-motorsports-digest-qzme
title: Add Bluesky as a data source
status: todo
type: feature
priority: normal
created_at: 2026-07-10T16:05:24Z
updated_at: 2026-07-11T19:48:41Z
parent: daily-motorsports-digest-z6pt
---

Integrate Bluesky API to pull posts about motorsports series, drivers, teams, and events for community signals and engagement metrics

## Value assessment (2026-07-11, live-probed)

**Strategic context:** score.py gives the reddit signal weight 0.5 (largest of 3), but Reddit is disabled -> reddit_raw=0 for every story -> rank_normalize ties them at 0.5 -> buzz collapses to flat ~0.50x. The dominant ranking dimension is currently dead. Bluesky's real value = revive that community-engagement signal.

**Access:** AT Protocol AppView is up; unauthenticated reads work but app.bsky.feed.searchPosts returns 403/401 -> needs a session. Session = free instant app password, NO manual approval / Responsible Builder gate (the reason Reddit is off). Confirmed working.

**Live 24h probe (sort=top, 100/query cap):**
- F1 volume is real: series/driver terms routinely hit the 100 cap; engagement F1=849, Grand Prix=475, Hamilton=1723, Russell=2554, Norris=306. ~53% of posts carry external article links (535/1015).
- Two problems: (1) keyword NOISE is severe — top-engagement posts on bare surnames are often off-topic (Bertrand Russell, Chuck/Christopher Norris, the 1966 'Grand Prix' film, French tax posts). (2) IndyCar is ~dead on Bluesky: Palou=1, Newgarden=1, O'Ward=3, IndyCar=28, Penske=2.

**Model decision -> A (per-story URL match), NOT per-entity keyword engagement.**
For each clustered Story (already has canonical_url + domains), find Bluesky posts embedding that article URL, sum like+repost+reply into the reddit_raw slot. Inherently noise-resistant (an off-topic post won't link an F1 article) and mirrors how the Reddit signal was meant to work. The ~53% link density makes it viable.

**Verdict:** Worth building, F1-focused, via URL matching, ~1 day. Revives the F1 half of the community signal; IndyCar stays flat. Independent quick win first: reweight scoring so it stops leaning on the dead reddit signal (see follow-up task).
