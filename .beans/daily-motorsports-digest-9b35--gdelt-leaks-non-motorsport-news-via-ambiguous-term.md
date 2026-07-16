---
# daily-motorsports-digest-9b35
title: GDELT leaks non-motorsport news via ambiguous terms + query-label series hint
status: completed
type: bug
priority: high
created_at: 2026-07-16T18:25:54Z
updated_at: 2026-07-16T18:47:49Z
parent: daily-motorsports-digest-z6pt
---

Live GDELT probe (2026-07-16): ~45 of 79 articles passing is_relevant() are not motorsport.

## Two distinct causes

1. **Ambiguous bare terms.** f1/indycar terms are sent to GDELT as *search keywords* against a general world-news corpus, then is_relevant() re-checks the *same* list — so the filter cannot catch what the query pulled in. Bare surnames leak: `Hamilton` (Hamilton ON city politics, Hamilton County OH, Alexander Hamilton, Hamilton Insurance Group NYSE:HG), `Russell` (golfer, musician, CFPB director, Russell 1000 ETF), `Alonso` (Xabi Alonso, football), `Leclerc` (French antique-car restorer), `Norris` (obituary), `Dixon`.

2. **Query label used as series hint.** fetch_gdelt() stamps `series=kind` on every row a query returns; classify_series() lets the source hint beat title matching (normalize.py:43). So `Penske` pulls NASCAR into the indycar query and those stories get force-labeled indycar — plus F1 stories returned by the indycar query become indycar. Mislabeled stories also wrongly claim core_floor protection.

The hint is correct for a curated RSS feed but is a lie for a keyword query: it records which query matched, not what the story is about.

## Fix
- [x] Anchor ambiguous f1/indycar terms (Lewis Hamilton, George Russell, Lando Norris, Charles Leclerc, Fernando Alonso, Scott Dixon)
- [x] Drop Penske/Ganassi from indycar terms (multi-series teams)
- [x] Stop passing the query label as a series hint from GDELT; classify by title
- [x] Regression tests for both
- [x] Update config.example.toml + live config.toml on the Pi

## Note on bean 98y5
98y5 rates this class low-risk because "sources are motorsport-only RSS + f1/indycar-scoped GDELT". That premise is wrong: GDELT is scoped *only* by these keywords, so a bare surname is a live pipe from world news, not a latent risk. 98y5's remaining collisions (NASCAR/FormulaE/endurance) stay low — those series are not queried against GDELT.

## Summary of Changes

Shipped in 521edcd; live config patched on the Pi and verified there.

- f1 terms: driver names anchored in full (Lewis Hamilton, Lando Norris, Charles Leclerc, George Russell, Fernando Alonso). Verstappen/Piastri left bare — already unambiguous.
- indycar terms: `Dixon` -> `Scott Dixon`; `Penske`/`Ganassi` dropped (multi-series teams).
- gdelt.py: `parse_articles()` no longer takes or sets `series`. The query label is not evidence of a story's series, and classify_series() lets a source hint beat the title — so labeling by query filed NASCAR/F1 stories under indycar and gave them core_floor slots they had not earned. normalize_items() now classifies GDELT rows by title.
- New tests/test_shipped_config_terms.py guards the *shipped* config.example.toml against the real junk headlines the live probe returned; the pre-existing term tests used a hand-built registry and so could never catch a bad term in the real config.

## Verification

Live dry-run on the Pi (2026-07-16, post-fix): 15/15 stories genuine motorsport, zero leaks. Real Lewis Hamilton and Charles Leclerc stories still came through, which was the main risk of anchoring. Before the fix, ~45 of 79 GDELT articles were non-motorsport.

## Deliberately not done

- Bare `Grand Prix` kept. It leaked 3 of ~46 (Hungarian Athletics Grand Prix, SailGP, a Spanish TV show), but dropping it loses legit headlines naming no driver or series ("Las Vegas Grand Prix sponsorship deal"), and anchoring means enumerating every race. See follow-up.
- The Pi's live config.toml has a dead `[keywords]` section (series_f1/teams/drivers/anchors, incl. bare "Hamilton") left from the pre-registry design. Nothing reads it — load_config() only reads series/tier/rss_feeds/subreddits/ses — so it did not contribute to this bug. See follow-up.
