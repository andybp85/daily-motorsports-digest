---
# daily-motorsports-digest-lm78
title: Bare "Grand Prix" leaks non-motorsport Grands Prix
status: todo
type: bug
priority: low
created_at: 2026-07-16T18:48:23Z
updated_at: 2026-07-16T18:48:23Z
parent: daily-motorsports-digest-z6pt
---

Residual from [[daily-motorsports-digest-9b35]], which anchored the driver surnames but left `Grand Prix` bare in the f1 terms.

"Grand Prix" is a general sporting term. The live probe caught 3 of ~46 leaks through it:
- "Charamba claims 200m silver at Hungarian Athletics Grand Prix"
- "SailGP 2030: la liga pone rumbo a la expansion mundial ... Spain Sail Grand Prix"
- "El Grand Prix del verano, por Neus Navarro" (Spanish TV show)

## Why it was left

Dropping it costs legitimate F1 headlines that name no driver and no series term — e.g. "LVCVA approves $100M sponsorship deal for Las Vegas Grand Prix through 2037". Anchoring means enumerating every race ("Belgian Grand Prix", "Las Vegas Grand Prix", ...), which is a maintenance burden and breaks on new events.

## Options

- Enumerate the calendar (accurate, high upkeep — the calendar changes yearly).
- Add a small exclusion list checked before the term match ("Athletics Grand Prix", "Sail Grand Prix"). New machinery for a 3-in-79 problem; weigh against YAGNI.
- Accept it. 3 junk stories a day is a low tax, and they compete on buzz like anything else.

Only worth doing if the residue proves annoying in practice. Recheck after a week of clean digests.

- [ ] Decide between the options above
- [ ] Add cases to tests/test_shipped_config_terms.py NON_MOTORSPORT_HEADLINES if fixed
