---
# daily-motorsports-digest-l2lf
title: 'Multi-series expansion: registry gate + core-guaranteed 15'
status: todo
type: feature
created_at: 2026-07-14T02:12:27Z
updated_at: 2026-07-14T02:12:27Z
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
