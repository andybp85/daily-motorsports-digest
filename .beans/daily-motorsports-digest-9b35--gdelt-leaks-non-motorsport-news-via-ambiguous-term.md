---
# daily-motorsports-digest-9b35
title: GDELT leaks non-motorsport news via ambiguous terms + query-label series hint
status: in-progress
type: bug
priority: high
created_at: 2026-07-16T18:25:54Z
updated_at: 2026-07-16T18:38:42Z
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
- [ ] Update config.example.toml + live config.toml on the Pi

## Note on bean 98y5
98y5 rates this class low-risk because "sources are motorsport-only RSS + f1/indycar-scoped GDELT". That premise is wrong: GDELT is scoped *only* by these keywords, so a bare surname is a live pipe from world news, not a latent risk. 98y5's remaining collisions (NASCAR/FormulaE/endurance) stay low — those series are not queried against GDELT.
