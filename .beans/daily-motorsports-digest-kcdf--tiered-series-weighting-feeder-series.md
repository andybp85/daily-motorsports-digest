---
# daily-motorsports-digest-kcdf
title: Tiered series weighting + feeder series
status: completed
type: feature
priority: normal
created_at: 2026-07-15T14:45:22Z
updated_at: 2026-07-15T16:08:37Z
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
- [x] Deploy to Pi (pull + reconcile config + venv + manual run)

## Summary of Changes

Generalized the flat core_series/core_floor gate into ordered priority tiers (models.Tier, gate.select_digest, config._parse_tiers). Floors applied top-down; earlier tiers never evicted by later ones under scarcity; untiered series compete on buzz only. Added F1/IndyCar feeder ladders (F2, F3, F1 Academy, Indy NXT), listed before parents in the registry so specific hits win classification. Tier floors validated to sum <= max_stories. Email order unchanged (buzz-desc). 100 tests pass. Shipped as commit c644931.

### Deploy (pi.home)
Pi was 17 commits behind AND its config.toml was pre-expansion (max_stories=8, no [[series]] registry) — the true cause of the 8-article mornings. Pulled to c644931, backed up config.toml -> config.toml.bak, bumped max_stories 8->15, appended the tested tier + series blocks. Dry-run produced 15 stories (up from 8); NASCAR reached the digest via its Tier-4 floor. New code/config takes effect at the next 06:00 timer.

### Follow-ups noted
- One GDELT call (indycar) hit the 30s cap; 10-series collection runs ~5 min sequentially — candidate for parallelizing GDELT.
- Dry-run surfaced a Hamilton false positive (Hamilton, Ontario data-centre story matched the F1 driver term) — pre-existing collision tracked by bean 98y5.
