---
# daily-motorsports-digest-pxca
title: Digest ranking has no working per-story signal
status: todo
type: bug
priority: high
created_at: 2026-07-11T19:50:41Z
updated_at: 2026-07-11T19:50:41Z
---

Measured 2026-07-11: on an 18-story RSS pool, ALL three ranking signals are effectively flat, so buzz is 0.500 for every story (1 distinct score / 18). Reweighting is a no-op — verified across reddit.5/breadth.35/spike.15, reddit.0/breadth.70/spike.30, reddit.0/breadth.85/spike.15: all give 1 distinct score.

Root causes:
- reddit (weight 0.5): Reddit disabled -> reddit_raw=0 for all -> tied at rank 0.5. Dead dominant signal.
- breadth (0.35): cluster_items merges only on exact URL or fuzzy title token_sort_ratio>=88. Different outlets rephrase headlines, so cross-outlet merges almost never happen -> every story is a singleton -> breadth=1 for all (18/18). Confirmed also in prod dry-run: top 8 all '(1 outlets)'.
- spike (0.15): GDELT per-series ratio; varies only between series (all f1 share one value, all indycar another) and often neutral/failed. Cannot rank within a series. This is the only thing that ever moves buzz in prod (hence 0.510/0.513).

Net: within a series the digest order is essentially arbitrary (stable-sort input order). The email 'top 8' is not meaningfully ranked.

## Fixes (candidates)
- [ ] Add a real per-story signal — Bluesky model A (bean qzme): per-story article-URL engagement into reddit_raw. Highest-leverage.
- [ ] Improve cross-outlet clustering so breadth actually varies (lower/normalize title matching; match on normalized URL/canonical link; consider shared external-link identity) — would make breadth a real importance proxy.
- [ ] Only after a signal exists: re-tune weights.

## Notes
Do NOT ship a weight change alone — measured no-op until an underlying signal varies.
