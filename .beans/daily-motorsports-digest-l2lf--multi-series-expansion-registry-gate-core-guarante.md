---
# daily-motorsports-digest-l2lf
title: 'Multi-series expansion: registry gate + core-guaranteed 15'
status: completed
type: feature
priority: normal
created_at: 2026-07-14T02:12:27Z
updated_at: 2026-07-14T12:34:09Z
parent: daily-motorsports-digest-z6pt
---

Implement the approved design in docs/superpowers/specs/2026-07-13-multi-series-expansion-design.md.

Add WEC, IMSA, NASCAR, Formula E via a per-series keyword registry that replaces the flat [keywords] gate (closes the manufacturer/anchor leak), and raise max_stories to 15 filled by a core-guaranteed floor for F1+IndyCar.

## Todo
- [ ] config: SeriesDef registry + core_series/core_floor; parse [[series]]; max_stories=15
- [ ] normalize: classify_series/is_relevant/normalize_items on registry; delete teams/drivers/anchors heuristic
- [ ] gate: select_digest core-guaranteed floor; wire into main.run
- [ ] config.toml + config.example.toml: series blocks (f1/indycar/wec/imsa/nascar/formulae)
- [ ] tests: normalize leak regression, select_digest floor cases, config parsing
- [ ] README + docs (satisfies bean qvrs)

Relates: WEC a6b9, IMSA xya5, NASCAR r7sq, Formula E 1fe9, docs qvrs.

## Summary of Changes

Shipped on main (merge 328d617). Executed as 5 reviewed tasks + Opus whole-branch review.

- SeriesDef registry + config parsing ([[series]] blocks, core_series, core_floor).
- Relevance gate rewritten to registry-based classification: keep iff a story classifies to a followed series; deleted the leaky teams/drivers/anchors heuristic; source_series feed hint now gated on registry membership (closes the last leak path). Migrated normalize/gdelt/pipeline/main off the removed cfg.keywords dict.
- select_digest: core-guaranteed floor (F1+IndyCar), fill by buzz, max_stories 8->15.
- Enabled WEC, IMSA, NASCAR, Formula E (six series). GDELT spike stays F1/IndyCar-only; new series rank on social + breadth.
- README documents the registry + how to add a series (satisfies qvrs).

96 tests passing. Dry-run: 15 stories, F1/IndyCar/NASCAR/IMSA surfaced.

Deferred (not done): config term-collision tightening (Gen3->Supercars; Penske/Ganassi cross-labeling); empty-[[series]] fail-fast; repo-wide ruff reformat.
