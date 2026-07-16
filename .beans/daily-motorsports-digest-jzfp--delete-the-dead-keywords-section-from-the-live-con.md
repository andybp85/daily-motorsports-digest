---
# daily-motorsports-digest-jzfp
title: Delete the dead [keywords] section from the live config
status: completed
type: task
priority: low
created_at: 2026-07-16T18:47:59Z
updated_at: 2026-07-16T19:30:56Z
parent: daily-motorsports-digest-z6pt
---

The Pi live config.toml still carries a `[keywords]` block (series_f1, series_indycar, teams, drivers, anchors) left from the pre-registry design, including a bare "Hamilton" and Penske/Ganassi.

Nothing reads it: load_config() only reads `series`, `tier`, `rss_feeds`, `subreddits`, `ses`. It did NOT contribute to the leak fixed in [[daily-motorsports-digest-9b35]] — verified by the post-fix dry-run being clean while the block was still present.

Worth deleting so it stops looking authoritative: the next person to tune terms could edit it and see no effect, or read its bare "Hamilton" as the live config.

- [ ] Remove [keywords] from the Pi live config.toml (gitignored — must be done on the Pi)
- [ ] Confirm no such block lingers in config.example.toml

Also note: the local dev config.toml is stale vs the Pi (missing [[tier]] blocks and the f2/f3/f1academy/indynxt feeder series, bluesky_enabled differs). Local dry-runs therefore exercise a different registry than production. Worth reconciling.

## Summary of Changes

Both done on 2026-07-16.

- Dropped the dead `[keywords]` table from the Pi's live config.toml (backup: `config.toml.pre-keywords-drop`). Confirmed dead first: nothing outside stale `.pyc` files references `keywords`/`series_f1`/`drivers`/`anchors`. Post-drop the config still loads with all 10 series and all 4 tiers intact. config.example.toml never had the block.
- Reconciled the local dev config.toml with the Pi by copying the Pi's down verbatim (backup: `config.toml.local-stale-backup`). The local copy had been missing the `[[tier]]` blocks and the f2/f3/f1academy/indynxt feeder series, and had `bluesky_enabled = false` vs the Pi's `true` — so local dry-runs were exercising a 6-series, single-tier registry while production ran 10 series across 4 tiers. They are now byte-identical. 104 tests pass against it.

## Note

config.toml is gitignored, so this parity is a point-in-time fix, not an enforced invariant — it can drift again. Worth a follow-up if it does; not building machinery for it now.
