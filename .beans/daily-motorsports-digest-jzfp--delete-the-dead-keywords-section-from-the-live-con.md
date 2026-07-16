---
# daily-motorsports-digest-jzfp
title: Delete the dead [keywords] section from the live config
status: todo
type: task
priority: low
created_at: 2026-07-16T18:47:59Z
updated_at: 2026-07-16T18:48:59Z
parent: daily-motorsports-digest-z6pt
---

The Pi live config.toml still carries a `[keywords]` block (series_f1, series_indycar, teams, drivers, anchors) left from the pre-registry design, including a bare "Hamilton" and Penske/Ganassi.

Nothing reads it: load_config() only reads `series`, `tier`, `rss_feeds`, `subreddits`, `ses`. It did NOT contribute to the leak fixed in [[daily-motorsports-digest-9b35]] — verified by the post-fix dry-run being clean while the block was still present.

Worth deleting so it stops looking authoritative: the next person to tune terms could edit it and see no effect, or read its bare "Hamilton" as the live config.

- [ ] Remove [keywords] from the Pi live config.toml (gitignored — must be done on the Pi)
- [ ] Confirm no such block lingers in config.example.toml

Also note: the local dev config.toml is stale vs the Pi (missing [[tier]] blocks and the f2/f3/f1academy/indynxt feeder series, bluesky_enabled differs). Local dry-runs therefore exercise a different registry than production. Worth reconciling.
