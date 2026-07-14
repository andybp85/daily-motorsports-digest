---
# daily-motorsports-digest-98y5
title: Disambiguate cross-series classification terms
status: todo
type: task
priority: low
created_at: 2026-07-14T12:36:02Z
updated_at: 2026-07-14T12:36:02Z
parent: daily-motorsports-digest-z6pt
---

Some [[series]] terms in config classify content into the wrong (or an unfollowed) series. Low risk today because sources are motorsport-only RSS + f1/indycar-scoped GDELT, but matters if a broad general feed is ever added.

## Collisions to fix
- `Gen3` (Formula E) also names Supercars' current-gen cars -> a Supercars story tags `formulae` (unfollowed-series leak vector). Consider dropping bare `Gen3`.
- `Penske` / `Ganassi` (IndyCar) also field IMSA/WEC entries -> those endurance stories mislabel as `indycar` AND wrongly claim core_floor protection. Consider removing from indycar terms or anchoring.
- `Xfinity` (Comcast brand), `Bristol` (city/other), `Elliott`/`Larson` (common surnames) under NASCAR -> would classify unrelated titles if a general feed is added. Consider anchoring: `NASCAR Xfinity`, `Bristol Motor Speedway`.

## Tradeoff
Tightening risks dropping legit stories (e.g. a real FE Gen3 headline). Only worth doing before adding a broad/general content source. Edit both the live config.toml (gitignored) and config.example.toml.
