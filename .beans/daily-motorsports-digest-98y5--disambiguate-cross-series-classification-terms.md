---
# daily-motorsports-digest-98y5
title: Disambiguate cross-series classification terms
status: todo
type: task
priority: low
created_at: 2026-07-14T12:36:02Z
updated_at: 2026-07-16T18:29:50Z
parent: daily-motorsports-digest-z6pt
blocked_by:
    - daily-motorsports-digest-9b35
---

Some [[series]] terms in config classify content into the wrong (or an unfollowed) series. Low risk today because sources are motorsport-only RSS + f1/indycar-scoped GDELT, but matters if a broad general feed is ever added.

## Collisions to fix
- `Gen3` (Formula E) also names Supercars' current-gen cars -> a Supercars story tags `formulae` (unfollowed-series leak vector). Consider dropping bare `Gen3`.
- `Penske` / `Ganassi` (IndyCar) also field IMSA/WEC entries -> those endurance stories mislabel as `indycar` AND wrongly claim core_floor protection. Consider removing from indycar terms or anchoring.
- `Xfinity` (Comcast brand), `Bristol` (city/other), `Elliott`/`Larson` (common surnames) under NASCAR -> would classify unrelated titles if a general feed is added. Consider anchoring: `NASCAR Xfinity`, `Bristol Motor Speedway`.

## Tradeoff
Tightening risks dropping legit stories (e.g. a real FE Gen3 headline). Only worth doing before adding a broad/general content source. Edit both the live config.toml (gitignored) and config.example.toml.

## Premise correction (2026-07-16)

The framing above — \"Low risk today because sources are motorsport-only RSS + f1/indycar-scoped GDELT\" — was wrong, and bean 9b35 fixed the fallout. GDELT is *general world news*; it is scoped only by the f1/indycar terms themselves. A bare surname there is a live pipe from world news into the digest, not a latent risk gated behind adding a general feed. A live probe found ~45 of 79 GDELT articles were non-motorsport.

9b35 has since anchored the f1/indycar driver names and dropped Penske/Ganassi, and stopped GDELT stamping its query label as a series hint.

## What is still open here

The remaining collisions are genuinely low risk, for the reason the original bean *meant*: these series are reached only via motorsport-only RSS, and are never sent to GDELT as keywords.

- `Gen3` (Formula E) also names Supercars' current-gen cars.
- `Xfinity`, `Bristol`, `Elliott`, `Larson` (NASCAR) — brand/city/common surnames.
- Endurance-series terms vs. their shared manufacturer names.

Re-rank this to high the moment any series beyond f1/indycar is added to the GDELT query, or any broad/general feed is added — that flips these from latent to live, exactly as it did for Hamilton.
