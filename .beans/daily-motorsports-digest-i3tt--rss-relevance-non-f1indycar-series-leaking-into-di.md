---
# daily-motorsports-digest-i3tt
title: 'RSS relevance: non-F1/IndyCar series leaking into digest'
status: completed
type: bug
priority: normal
created_at: 2026-07-10T13:02:44Z
updated_at: 2026-07-10T13:40:36Z
---

Dry-run on the Pi (2026-07-10) selected off-topic stories in the F1/IndyCar digest:

- #3 Vinales / KTM contract  -> MotoGP
- #7 Bagnaia title fight     -> MotoGP
- #4 Supercars Townsville    -> Supercars
- #8 Monaco Formula E        -> Formula E

RSS feeds (autosport, the-race, motorsport.com) carry all series; classification/relevance filtering should scope to F1 + IndyCar only. GDELT path uses is_relevant() (series/team/driver + anchor), but RSS normalization/classification apparently does not gate as tightly.

Next: check how RSS entries get a series and whether unmatched-series items are dropped. Likely the classifier assigns a default series instead of excluding. Add an is_relevant-style gate to the RSS path (or a shared relevance filter across collectors).

## Summary of Changes

Root cause: normalize_items kept every item, tagging non-F1/IndyCar stories series="" instead of dropping them. Only the GDELT path filtered (is_relevant); RSS had no gate.

Fix (commit 38f1280):
- Moved is_relevant from collect/gdelt.py to normalize.py (relevance is a normalization concern shared by all collectors; gdelt imports it from there).
- normalize_items now drops an item unless it classifies to a followed series OR passes is_relevant (series/team term, or driver+anchor).
- Tests: moved is_relevant tests to test_normalize; added drop-gate tests (off-topic dropped, team-story kept with series="", source-series feed trusted). 67 pass.

Tuning (commit 05604b8):
- Gate over-dropped 'GP'-abbreviated F1 stories (keywords had only 'Grand Prix'). Added GP/practice/sprint to anchors (safe: anchors only gate a bare driver name; kept out of series lists that feed the GDELT query).

Verified on Pi (real RSS): 31 raw -> 19 kept, 12 dropped. Dropped = Supercars/MotoGP/Formula E/WRC/NASCAR. Rescued the two Russell GP stories.

Known edge: an anchor-only F1 story with no driver/team/series term (e.g. 'German GP practice') still drops; rescuing it needs 'GP' as a series term, which would pollute the GDELT query. Left as-is.
