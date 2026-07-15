---
# daily-motorsports-digest-kcdf
title: Tiered series weighting + feeder series
status: in-progress
type: feature
priority: normal
created_at: 2026-07-15T14:45:22Z
updated_at: 2026-07-15T15:44:14Z
---

Generalize the flat core_series/core_floor gate into ordered tiers with per-tier floors, and add F1/IndyCar feeder series (F2, F3, F1 Academy, Indy NXT).

## Tiers (ordered, per-tier floor; cap=15)
- T1 f1, indycar — floor 6
- T2 f2, f3, f1academy, indynxt — floor 3
- T3 wec, formulae — floor 2
- T4 nascar, imsa — floor 2
- Untiered series — floor 0 (buzz fill only)

## Mechanism
Per-tier floors + buzz fill. Allocate each tier's floor in tier order (highest-buzz stories of that tier), then fill remaining slots by buzz across everything unchosen. Email display order stays buzz-desc (unchanged).

## Todo
- [x] Add Tier dataclass; load [[tier]] blocks in config.py
- [x] Validate tier series ids exist + sum(floors) <= max_stories
- [x] Generalize gate.select_digest to tiers (replace core_series/core_floor)
- [x] Wire tiers through main.py
- [x] Add feeder series defs (f2/f3/f1academy/indynxt) with disambiguated terms
- [x] Tests: floor allocation, scarcity, untiered fill, config validation
- [x] Update README + config.example.toml
- [ ] Deploy to Pi (pull + reconcile config + venv + manual run)
