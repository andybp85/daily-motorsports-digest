---
# daily-motorsports-digest-wuks
title: Add Substack RSS sources
status: todo
type: feature
priority: normal
created_at: 2026-07-12T00:30:05Z
updated_at: 2026-07-12T00:30:05Z
parent: daily-motorsports-digest-z6pt
---

Add curated Substack publication feeds as RSS content sources. Substack fits as CONTENT (RSS), not an engagement signal — every publication exposes https://<pub>.substack.com/feed, so it's just more [[rss_feeds]] entries in config.toml; zero code (fetch_rss + is_relevant gate + clustering already handle it).

## Why
Current feeds (Autosport, The Race, Motorsport.com, Racer) are wire-service news. Substack's value is independent analysis/opinion/insider voices the wires don't carry — real editorial diversity, and you pick exactly which voices (avoids the broad-feed leakage of WEC/MotoGP/NASCAR seen from autosport/all).

## Caveats
- Paywalled posts usually give only a teaser in RSS → summarizer gets headline + snippet, not full piece. Prefer free publications, or accept teasers.
- Adds depth, not volume (Substacks publish daily-ish or less).
- A lone Substack post is breadth=1; ranks well only with social traction — which the new Bluesky social signal (bean qzme) can now detect if the post is shared/linked. The two complement each other.
- Strong independent F1 presence; IndyCar thinner (mirrors the Bluesky asymmetry).

## Todo
- [ ] Pick specific active F1/IndyCar Substack publications (flag free vs paywalled)
- [ ] Add their /feed URLs to config.toml [[rss_feeds]] with series = "" (title-classified)
- [ ] Verify a dry-run: posts appear, pass is_relevant, cluster sanely, don't over-leak
- [ ] Confirm paywalled feeds still yield usable titles/teasers (or drop them)

The lever is WHICH publications — that selection is the real work here, not the wiring.
