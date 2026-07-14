# Multi-Series Expansion — Design

**Date:** 2026-07-13
**Status:** Approved (design)
**Epic:** daily-motorsports-digest-z6pt (Expand motorsports series coverage)

## Problem

Two coupled issues:

1. **The gate leaks.** `normalize.is_relevant` keeps any story whose title
   contains a **team name** (`Ferrari, McLaren, Aston Martin, Alpine, Porsche`…)
   or a **driver surname + generic anchor** (`racing`, `motorsport`, `circuit`…).
   Those manufacturer names also race in WEC/IMSA, and the anchors are generic,
   so non-F1/IndyCar content (a WEC "Ferrari 499P" story) sails through, gets
   tagged `series=""`, and lands in the digest. The leak is incidental name
   collision, not intent.

2. **Coverage is F1/IndyCar-only by design,** but the owner wants a broader
   field: WEC, IMSA, NASCAR, Formula E — arriving *because they were chosen*,
   not because a name happened to match.

Simply raising `max_stories` amplifies the leak. The fix is to make series
membership **intentional and data-driven**, then widen the digest on top of a
gate that no longer leaks.

## Goals

- Add four series — **WEC, IMSA, NASCAR, Formula E** — alongside F1 + IndyCar.
- Replace the flat `[keywords]` block with a **per-series registry**; a story is
  kept iff it classifies to a followed series. This closes the leak at the root.
- Raise `max_stories` to **15**, filled by a **core-guaranteed** rule: reserve a
  floor of slots for F1+IndyCar, then fill the rest by buzz.
- Adding a series later = drop in one config block. No code change.

## Non-Goals (YAGNI)

- SuperGT, BTCC, feeder series, event-specific tracking (Monaco/Daytona),
  YouTube/Substack sources — all remain deferred beans under z6pt.
- Per-series RSS feed sourcing. The existing broad feeds are re-sorted by the
  registry; dedicated feeds can be added later as ordinary `[[rss_feeds]]` rows.
- Multi-label stories. Each story gets exactly one series (majority vote across
  its cluster, as today).

## Approach — Series Registry (chosen over minimal-additive / feed-driven)

### Config shape

Replace the `[keywords]` table with an ordered list of series blocks:

```toml
max_stories = 15
core_series = ["f1", "indycar"]   # protected core
core_floor = 6                    # min slots reserved for the core (if available)

[[series]]
id = "f1"
label = "Formula 1"
terms = ["Formula 1", "Formula One", "F1", "Grand Prix",
         "Verstappen", "Hamilton", "Norris", "Leclerc", "Russell",
         "Piastri", "Alonso", "Red Bull Racing", "Scuderia Ferrari"]

[[series]]
id = "indycar"
label = "IndyCar"
terms = ["IndyCar", "Indy 500", "Indianapolis 500",
         "Palou", "Newgarden", "Dixon", "Herta", "O'Ward", "Penske", "Ganassi"]

[[series]]
id = "wec"
label = "WEC"
terms = ["WEC", "World Endurance", "Le Mans", "Hypercar", "LMGT3",
         "6 Hours of", "499P", "Toyota Gazoo", "Peugeot 9X8"]

[[series]]
id = "imsa"
label = "IMSA"
terms = ["IMSA", "WeatherTech", "GTP", "Rolex 24", "Daytona 24",
         "Sebring", "Petit Le Mans"]

[[series]]
id = "nascar"
label = "NASCAR"
terms = ["NASCAR", "Cup Series", "Xfinity", "Craftsman Truck",
         "Daytona 500", "Talladega", "Bristol", "Larson", "Elliott"]

[[series]]
id = "formulae"
label = "Formula E"
terms = ["Formula E", "FE ", "Gen3", "E-Prix", "ABB FIA"]
```

**Term design rules (this is the leak fix):**

- Terms are **distinctive identifiers**: series names, sanctioning bodies,
  signature events, and driver surnames that are unambiguous within the field.
- **Bare, ambiguous manufacturer names are excluded** as classification terms
  (`Ferrari`, `McLaren`, `Porsche` alone). They appear only in disambiguated
  forms (`Scuderia Ferrari`, `Toyota Gazoo`). A story that names only "Ferrari"
  with no series/event/driver term is dropped — accepted tradeoff: kills the
  dominant leak, and such a story is genuinely ambiguous.
- Ordering matters: `classify_series` returns the **first** series in list order
  whose term matches. Put the more specific/priority series earlier; F1 and
  IndyCar lead so a shared driver resolves to the core.

### Classification (`normalize.py`)

Introduce a typed registry and rewrite the two gate functions:

```python
@dataclass(frozen=True)
class SeriesDef:
    id: str
    label: str
    terms: tuple[str, ...]

def classify_series(title: str, source_series: str,
                    registry: tuple[SeriesDef, ...]) -> str:
    """Return a series id or '' — explicit source hint wins, else first term match."""
    if source_series:
        return source_series
    low = title.lower()
    for s in registry:
        if any(t.lower() in low for t in s.terms):
            return s.id
    return ""

def is_relevant(title: str, registry: tuple[SeriesDef, ...]) -> bool:
    """Kept iff the title classifies to some followed series."""
    return classify_series(title, "", registry) != ""
```

`normalize_items` takes `registry` instead of `keywords`. The
`teams`/`drivers`/`anchors` flat lists and the driver+anchor heuristic are
**deleted** — that heuristic is a primary leak source and the registry subsumes
its legitimate cases (driver surnames now live under their series).

The `source_series` hint still wins (e.g. `racer.com` feed → `indycar`),
preserving current feed behavior.

### Selection — core-guaranteed floor (`gate.py`)

Add a pure function; `main.run` calls it instead of the raw
`survivors[: cfg.max_stories]` slice:

```python
def select_digest(survivors: list[ScoredStory], *, max_stories: int,
                  core_series: set[str], core_floor: int) -> list[ScoredStory]:
    """Reserve a floor of slots for core series, fill the rest by buzz.

    `survivors` is already sorted by buzz descending.
    """
    core = [s for s in survivors if s.story.series in core_series]
    guaranteed = core[:core_floor]                      # floor, capped by availability
    guaranteed_keys = {id(s) for s in guaranteed}
    pool = [s for s in survivors if id(s) not in guaranteed_keys]
    fill = pool[: max(0, max_stories - len(guaranteed))]
    chosen = guaranteed + fill
    chosen.sort(key=lambda s: s.buzz, reverse=True)     # display order
    return chosen[:max_stories]
```

Notes:
- The floor is a **minimum, not a cap** — if core stories out-buzz everyone they
  fill more than `core_floor` naturally (they also appear in `pool`).
- If fewer than `core_floor` core stories exist, the remainder just goes to buzz;
  no slot is wasted.
- Ties/keys: identity (`id()`) dedup avoids equality pitfalls on ScoredStory.

## Data Flow (unchanged except gate + selection)

```
collect → normalize_items(registry)   # leak fixed here: keep iff classifies
        → cluster (_majority_series)   # Story.series now always a real id
        → score_pool                   # unchanged
        → filter_stories (gate)        # unchanged
        → select_digest(...)           # NEW: core-guaranteed, ≤15
        → email
```

## Config plumbing (`config.py`)

- Add fields: `series: tuple[SeriesDef, ...]`, `core_series: list[str]`,
  `core_floor: int`. Default `max_stories` bumps to 15.
- `load_config` parses `[[series]]` into `SeriesDef` tuples and reads
  `core_series` / `core_floor` (defaults `["f1","indycar"]` / `6`).
- Remove the `keywords` field once no caller references it.
- `pipeline.py:14` passes `cfg.series` to `normalize_items`.

## Error handling

- Empty/malformed `[[series]]` → `load_config` raises (fail fast; a digest with
  no registry keeps nothing and is a config error, not a silent empty send).
- `core_floor > max_stories` → clamp to `max_stories` at load with a warning;
  the selection math already tolerates it but clamping keeps intent honest.
- Unknown id in `core_series` (not matching any `[[series]].id`) → raise at load.

## Testing

- **normalize:** WEC "Ferrari 499P" title now **classifies to wec** (kept) — but
  a bare "Ferrari unveils road car" title is **dropped** (no term). F1 "Verstappen
  wins" classifies f1 via driver term. Feed `source_series` hint still wins.
  Regression test for the exact leak that motivated this (autosport/all WEC item).
- **select_digest:** floor honored when ≥`core_floor` core survivors; floor
  under-filled gracefully when fewer; high-buzz core exceeds floor; total capped
  at `max_stories`; result sorted by buzz for display.
- **config:** `[[series]]` parses to `SeriesDef`; bad `core_series` id raises;
  `core_floor` clamps.
- Existing `test_normalize.py` fixtures (`KEYWORDS`) migrate to a registry fixture.

## Rollout

`calibration = true` today (sends daily, threshold bypassed), so the wider gate
and 15-slot cap take effect on the next run with no threshold interplay. Watch
the calibration score log for a run or two to confirm the new series surface and
the core floor holds before tuning `threshold`.

## Docs

- Update `README.md` and `config.example.toml` for the registry shape,
  `core_series`/`core_floor`, and `max_stories = 15`.
- This satisfies bean **qvrs** ("Document: how to add new series") — the registry
  *is* the documented extension point.
