# Multi-Series Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WEC, IMSA, NASCAR, and Formula E to the digest via a per-series keyword registry that replaces the leaky flat-keyword gate, and raise the daily cap to 15 stories filled by a core-guaranteed floor for F1+IndyCar.

**Architecture:** A `SeriesDef` registry (one block per followed series, each carrying distinctive identifying terms) becomes the single source of truth for both *classification* (which series a story belongs to) and *relevance* (keep iff it classifies to a followed series). This closes the leak where shared manufacturer names (`Ferrari`, `Porsche`) and generic anchors (`racing`) let other-series content through. A pure `select_digest` function then reserves a floor of slots for the core series before filling the rest by buzz.

**Tech Stack:** Python 3.12+, `uv`, `pytest`, `ruff`. stdlib `tomllib` for config. No new dependencies.

**Design spec:** `docs/superpowers/specs/2026-07-13-multi-series-expansion-design.md`
**Tracking bean:** `daily-motorsports-digest-l2lf`

## Global Constraints

- **No new dependencies** — registry is plain dataclasses + `tomllib`.
- **Python conventions:** annotate every function signature (params + return); modern typing (`list[str]`, `X | None`); prefer dataclasses over loose dicts. Run `uv run ruff format` + `uv run ruff check` before every commit.
- **Every commit keeps the full suite green:** `uv run pytest`.
- **Series ids are lowercase slugs:** `f1`, `indycar`, `wec`, `imsa`, `nascar`, `formulae`.
- **Spec addendum (not in the written spec):** GDELT (`digest/collect/gdelt.py`) also consumes the old `keywords` dict and is hardcoded to F1/IndyCar for its spike signal. It stays F1/IndyCar-scoped (new series get a neutral spike of 1.0 via `score.py:37`), but its helpers migrate from `keywords: dict` to the registry in Task 2. No new GDELT calls are added — that would multiply GDELT's rate-limited requests.

---

### Task 1: Series registry type + config parsing (additive)

Add the `SeriesDef` type and parse `[[series]]` / `core_series` / `core_floor` from config. Keep the legacy `keywords` field intact so every other module still works — this task is purely additive and independently green. The full switch-over happens in Task 2.

**Files:**
- Modify: `digest/models.py` (add `SeriesDef`)
- Modify: `digest/config.py:1-66` (new fields + parsing + validation)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `SeriesDef(id: str, label: str, terms: tuple[str, ...])` — frozen dataclass in `digest/models.py`.
- Produces: `Config.series: tuple[SeriesDef, ...]`, `Config.core_series: list[str]`, `Config.core_floor: int`; `Config.max_stories` default becomes `15`. `Config.keywords` still exists after this task.
- Produces: `load_config` parses `[[series]]` blocks, `core_series`, `core_floor`; validates (see Step 3).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
from digest.models import SeriesDef


def test_load_config_parses_series_registry(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(textwrap.dedent("""
        max_stories = 15
        core_series = ["f1", "indycar"]
        core_floor = 6

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1", "Grand Prix", "Verstappen"]

        [[series]]
        id = "wec"
        label = "WEC"
        terms = ["WEC", "Le Mans", "Hypercar"]
    """))
    cfg = load_config(str(cfg_file))
    assert cfg.max_stories == 15
    assert cfg.core_series == ["f1", "indycar"]
    assert cfg.core_floor == 6
    assert [s.id for s in cfg.series] == ["f1", "wec"]
    assert cfg.series[0] == SeriesDef(id="f1", label="Formula 1",
                                      terms=("F1", "Grand Prix", "Verstappen"))


def test_load_config_clamps_core_floor_to_max_stories(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(textwrap.dedent("""
        max_stories = 3
        core_floor = 10
        core_series = ["f1"]

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1"]
    """))
    cfg = load_config(str(cfg_file))
    assert cfg.core_floor == 3          # clamped to max_stories


def test_load_config_rejects_unknown_core_series_id(tmp_path):
    import pytest
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(textwrap.dedent("""
        core_series = ["motogp"]

        [[series]]
        id = "f1"
        label = "Formula 1"
        terms = ["F1"]
    """))
    with pytest.raises(ValueError, match="core_series"):
        load_config(str(cfg_file))
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run pytest tests/test_config.py::test_load_config_parses_series_registry -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'series'` (and `ImportError` for `SeriesDef`).

- [ ] **Step 3: Add `SeriesDef` to `digest/models.py`**

At the top of `digest/models.py`, after the existing imports, add:

```python
@dataclass(frozen=True)
class SeriesDef:
    """One followed motorsport series and the title terms that identify it."""
    id: str                           # lowercase slug: "f1", "wec", ...
    label: str                        # display name: "Formula 1", "WEC"
    terms: tuple[str, ...]            # distinctive identifiers; substring-matched
```

- [ ] **Step 4: Add fields + parsing + validation to `digest/config.py`**

In the `Config` dataclass (`digest/config.py:6-31`), change the `max_stories` default and add three fields (keep `keywords` for now). Import `SeriesDef`:

```python
from digest.models import SeriesDef
```

```python
    max_stories: int = 15
    series: tuple[SeriesDef, ...] = ()
    core_series: list[str] = field(default_factory=lambda: ["f1", "indycar"])
    core_floor: int = 6
```

Add a private parser above `load_config`:

```python
def _parse_series(raw: list[dict]) -> tuple[SeriesDef, ...]:
    """Build the series registry from [[series]] blocks, preserving order."""
    return tuple(
        SeriesDef(id=b["id"], label=b["label"], terms=tuple(b["terms"]))
        for b in raw
    )
```

In `load_config`, after `data = tomllib.load(fh)` and before building `cfg`, parse and validate:

```python
    series = _parse_series(data.get("series", []))
    core_series = data.get("core_series", ["f1", "indycar"])
    core_floor = int(data.get("core_floor", 6))

    max_stories = int(data.get("max_stories", 15))
    core_floor = min(core_floor, max_stories)          # floor can't exceed the cap

    if series:                                          # validate only once populated
        known = {s.id for s in series}
        unknown = [c for c in core_series if c not in known]
        if unknown:
            raise ValueError(f"core_series references unknown series id(s): {unknown}")
```

Then add to the `Config(...)` constructor call the new keyword args, and replace the inline `max_stories=int(data.get("max_stories", 8))` with `max_stories=max_stories`:

```python
        max_stories=max_stories,
        series=series,
        core_series=core_series,
        core_floor=core_floor,
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS — all config tests, including the three new ones. The pre-existing `test_load_config_reads_toml_and_env` still passes (it has no `[[series]]`, so `series` is empty and validation is skipped).

- [ ] **Step 6: Lint + commit**

```bash
uv run ruff format digest/models.py digest/config.py tests/test_config.py
uv run ruff check digest/models.py digest/config.py tests/test_config.py
git add digest/models.py digest/config.py tests/test_config.py
git commit -m "feat: add SeriesDef registry parsing to config (additive)"
```

---

### Task 2: Switch the gate to the registry (atomic migration off `keywords`)

Rewrite `classify_series` / `is_relevant` / `normalize_items` to consume the registry, delete the leaky `teams`/`drivers`/`anchors` heuristic, and migrate every remaining `keywords` consumer (GDELT, pipeline, main) in the same commit. Remove the `Config.keywords` field at the end. This is one atomic type migration — it cannot be split without leaving the build red, because these modules share the `is_relevant` signature.

**Files:**
- Modify: `digest/normalize.py:33-75`
- Modify: `digest/collect/gdelt.py:67-95,141-182`
- Modify: `digest/pipeline.py:14`
- Modify: `digest/main.py:25`
- Modify: `digest/config.py` (remove `keywords` field + its parse line)
- Modify: `digest/models.py:15,25` (comment only — series is now any followed id)
- Test: `tests/test_normalize.py`, `tests/test_gdelt.py`, `tests/test_pipeline.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: `SeriesDef` (Task 1).
- Produces (new signatures):
  - `classify_series(title: str, source_series: str, registry: tuple[SeriesDef, ...]) -> str`
  - `is_relevant(title: str, registry: tuple[SeriesDef, ...]) -> bool`
  - `normalize_items(items: list[RawItem], registry: tuple[SeriesDef, ...]) -> list[RawItem]`
  - `build_keyword_list(registry: tuple[SeriesDef, ...], kind: str) -> list[str]`
  - `parse_articles(rows: list[dict], registry: tuple[SeriesDef, ...], series: str = "") -> list[RawItem]`
  - `fetch_gdelt(registry: tuple[SeriesDef, ...], since, end, client=None, timeout=...) -> tuple[list[RawItem], dict[str, float]]`
- After this task `Config.keywords` no longer exists.

- [ ] **Step 1: Rewrite `tests/test_normalize.py` for registry + leak behavior**

Replace the top-of-file `KEYWORDS` dict and the affected tests. New fixture and tests:

```python
from digest.models import RawItem, SeriesDef
from digest.normalize import canonicalize_url, classify_series, is_relevant, normalize_items

REGISTRY = (
    SeriesDef(id="f1", label="Formula 1",
              terms=("Formula 1", "F1", "Grand Prix", "Verstappen")),
    SeriesDef(id="indycar", label="IndyCar",
              terms=("IndyCar", "Indy 500", "Palou")),
    SeriesDef(id="wec", label="WEC",
              terms=("WEC", "Le Mans", "Hypercar", "499P")),
)


def test_classify_series_prefers_source_hint():
    assert classify_series("Some ambiguous headline", "indycar", REGISTRY) == "indycar"


def test_classify_series_from_title_terms():
    assert classify_series("Verstappen wins the Grand Prix", "", REGISTRY) == "f1"
    assert classify_series("Palou dominates at Indy 500", "", REGISTRY) == "indycar"
    assert classify_series("Unrelated tech news", "", REGISTRY) == ""


def test_classify_series_first_match_wins_in_registry_order():
    # A title that could hit two series resolves to the earlier (core) one.
    assert classify_series("Verstappen tests at Le Mans", "", REGISTRY) == "f1"


def test_normalize_items_sets_domain_and_series():
    item = RawItem(source="rss", url="https://www.autosport.com/f1/?utm_source=z",
                   title="Verstappen upgrade for the Grand Prix")
    out = normalize_items([item], REGISTRY)[0]
    assert out.url == "https://www.autosport.com/f1"
    assert out.domain == "www.autosport.com"
    assert out.series == "f1"


def test_is_relevant_keeps_classified_story():
    assert is_relevant("Verstappen's new F1 upgrade", REGISTRY) is True


def test_is_relevant_rejects_unclassifiable_story():
    assert is_relevant("Alex Palou opens a coffee shop", REGISTRY) is True   # 'Palou' term
    assert is_relevant("Local council debates parking", REGISTRY) is False


def _rss(title: str, series: str = "") -> RawItem:
    return RawItem(source="rss", url="https://motorsport.com/x", title=title, series=series)


def test_normalize_drops_off_topic_series():
    # Series NOT in the registry (MotoGP, Supercars) must be dropped.
    off_topic = [
        _rss("Vinales: 'KTM sent me a contract'"),          # MotoGP
        _rss("Supercars Townsville: Waters takes win"),      # Supercars
    ]
    assert normalize_items(off_topic, REGISTRY) == []


def test_normalize_keeps_chosen_series_via_registry():
    # The leak fix, inverted: a WEC story now classifies and is KEPT (wec is followed).
    out = normalize_items([_rss("Ferrari 499P wins at Le Mans")], REGISTRY)
    assert len(out) == 1 and out[0].series == "wec"


def test_normalize_drops_bare_ambiguous_manufacturer():
    # 'Ferrari' alone, no series/event/driver term → dropped (the old leak source).
    assert normalize_items([_rss("Ferrari unveils new road-going hypercar")], REGISTRY) == []


def test_normalize_trusts_source_series_feed():
    out = normalize_items([_rss("Grosjean signs multi-year deal", series="indycar")], REGISTRY)
    assert len(out) == 1 and out[0].series == "indycar"
```

Keep the three `canonicalize_*` tests unchanged.

- [ ] **Step 2: Run to verify the new normalize tests fail**

Run: `uv run pytest tests/test_normalize.py -v`
Expected: FAIL — `classify_series` / `is_relevant` / `normalize_items` still take a `keywords` dict, so registry calls raise `AttributeError` / behave wrong.

- [ ] **Step 3: Rewrite `digest/normalize.py` (lines 33-75)**

Replace `classify_series`, `is_relevant`, and `normalize_items`. Delete the driver+anchor heuristic entirely. Add the import:

```python
from digest.models import RawItem, SeriesDef
```

```python
def classify_series(title: str, source_series: str,
                    registry: tuple[SeriesDef, ...]) -> str:
    """Return a followed series id, or '' — source hint wins, else first term match.

    Registry order is priority: a title matching two series resolves to the
    earlier one (the core series lead), so shared driver/manufacturer names
    fall to F1/IndyCar rather than an endurance series.
    """
    if source_series:
        return source_series
    low = title.lower()
    for series in registry:
        if any(term.lower() in low for term in series.terms):
            return series.id
    return ""


def is_relevant(title: str, registry: tuple[SeriesDef, ...]) -> bool:
    """Keep iff the title classifies to a followed series.

    This is the leak fix: a story is relevant only because it matches a series
    we chose, not because it happens to name a manufacturer or a generic
    motorsport word shared across series.
    """
    return classify_series(title, "", registry) != ""


def normalize_items(items: list[RawItem], registry: tuple[SeriesDef, ...]) -> list[RawItem]:
    """Return new items with canonical URL, extracted domain, and resolved series.

    Drops items that don't classify to a followed series — without this gate the
    general motorsport feeds (autosport, motorsport.com…) leak every series they
    carry into the digest.
    """
    out = []
    for it in items:
        series = classify_series(it.title, it.series, registry)
        if not series:
            continue
        url = canonicalize_url(it.url)
        domain = urlparse(url).netloc
        out.append(RawItem(
            source=it.source, url=url, title=it.title.strip(), domain=domain,
            published_at=it.published_at, reddit_score=it.reddit_score,
            reddit_comments=it.reddit_comments, series=series, extra=it.extra,
        ))
    return out
```

- [ ] **Step 4: Update `tests/test_gdelt.py` fixture + calls to the registry**

Replace the `KEYWORDS` dict with a `REGISTRY` and update the three call sites. `build_keyword_list` now returns the terms of the matching series:

```python
from digest.models import SeriesDef

REGISTRY = (
    SeriesDef(id="f1", label="Formula 1", terms=("Formula 1", "F1", "Grand Prix", "Verstappen")),
    SeriesDef(id="indycar", label="IndyCar", terms=("IndyCar", "Indy 500", "Palou")),
)


def test_build_keyword_list_scopes_to_series():
    f1 = build_keyword_list(REGISTRY, "f1")
    assert "F1" in f1 and "Grand Prix" in f1
    assert "Indy 500" not in f1          # not the other series


def test_parse_articles_filters_irrelevant():
    rows = [
        {"url": "https://a.com/1", "title": "Verstappen wins the Grand Prix", "domain": "a.com"},
        {"url": "https://b.com/2", "title": "Local news about a person named Smith", "domain": "b.com"},
    ]
    items = parse_articles(rows, REGISTRY)
    assert [i.url for i in items] == ["https://a.com/1"]
    assert items[0].source == "gdelt"


def test_parse_articles_tags_series():
    rows = [{"url": "https://a.com/1", "title": "Verstappen wins the Grand Prix", "domain": "a.com"}]
    items = parse_articles(rows, REGISTRY, series="f1")
    assert items[0].series == "f1"
```

And in `test_fetch_gdelt_survives_a_hanging_search`, pass `REGISTRY` instead of `KEYWORDS`:

```python
    articles, spikes = fetch_gdelt(
        REGISTRY, since, end, client=_HangingGdelt(), timeout=0.2
    )
```

- [ ] **Step 5: Migrate `digest/collect/gdelt.py` to the registry**

Replace `build_keyword_list` (lines 67-77), `parse_articles` (79-95), and the `fetch_gdelt` signature + its `Filters(keyword=...)` / `parse_articles(...)` calls (141-172). Update the import at line 7-8 region:

```python
from digest.models import RawItem, SeriesDef
```

```python
def build_keyword_list(registry: tuple[SeriesDef, ...], kind: str) -> list[str]:
    """The terms for one series id ('f1' | 'indycar'), or [] if not followed.

    Deliberately short: GDELT rejects an over-long keyword query, so we send one
    series' identifying terms and let is_relevant() do fine filtering downstream.
    """
    for series in registry:
        if series.id == kind:
            return list(series.terms)
    return []


def parse_articles(rows: list[dict], registry: tuple[SeriesDef, ...],
                   series: str = "") -> list[RawItem]:
    """Convert GDELT article rows into relevant RawItems."""
    items = []
    for row in rows:
        title = row.get("title", "")
        if not is_relevant(title, registry):
            continue
        items.append(
            RawItem(source="gdelt", url=row.get("url", ""), title=title,
                    domain=row.get("domain", ""), series=series)
        )
    return items
```

Change `fetch_gdelt`'s first parameter and its two internal uses:

```python
def fetch_gdelt(
    registry: tuple[SeriesDef, ...],
    since: datetime,
    end: datetime,
    client=None,
    timeout: float = _GDELT_CALL_TIMEOUT_S,
):
```

Inside the loop, replace `keyword=build_keyword_list(keywords, kind)` with `keyword=build_keyword_list(registry, kind)` and `parse_articles(rows, keywords, series=kind)` with `parse_articles(rows, registry, series=kind)`. The loop stays `for kind in ("f1", "indycar")` — GDELT remains the F1/IndyCar spike source (see Global Constraints addendum).

- [ ] **Step 6: Migrate `pipeline.py` and `main.py` call sites**

`digest/pipeline.py:14` — pass the registry:

```python
    normalized = normalize_items(raw_items, cfg.series)
```

`digest/main.py:25` — pass the registry to GDELT:

```python
    gdelt_items, spikes = fetch_gdelt(cfg.series, since, end)
```

Update `tests/test_pipeline.py` `_cfg()` (lines 14-20) to build a registry instead of `keywords`:

```python
from digest.models import RawItem, SeriesDef


def _cfg():
    return Config(
        calibration=True, suppress_days=3, escalation_factor=1.5,
        weights={"social": 0.5, "breadth": 0.35, "spike": 0.15},
        series=(
            SeriesDef(id="f1", label="Formula 1", terms=("F1", "Grand Prix")),
            SeriesDef(id="indycar", label="IndyCar", terms=("IndyCar",)),
        ),
    )
```

- [ ] **Step 7: Remove the `keywords` field from `Config` + its test assertion**

In `digest/config.py`: delete the `keywords: dict = field(default_factory=dict)` field and the `keywords=data.get("keywords", {}),` line in `load_config`.

In `tests/test_config.py::test_load_config_reads_toml_and_env`: delete the `[keywords]` block from the inline TOML (lines 36-41) and the final assertion `assert "Verstappen" in cfg.keywords["drivers"]` (line 58).

Update the comments in `digest/models.py:15` and `:25` from `# "f1" | "indycar" | ""` to `# a followed series id, or "" (RawItem, pre-classification)`.

- [ ] **Step 8: Run the full suite to verify green**

Run: `uv run pytest`
Expected: PASS — all tests. Grep to confirm no stragglers:

Run: `uv run python -c "import digest.config, digest.normalize, digest.pipeline, digest.main, digest.collect.gdelt"`
Expected: no `AttributeError`/`ImportError`. Also confirm nothing references `.keywords`:

Run: `grep -rn "keywords" digest/ tests/`
Expected: no matches (or only unrelated comments).

- [ ] **Step 9: Lint + commit**

```bash
uv run ruff format digest/ tests/
uv run ruff check digest/ tests/
git add digest/ tests/
git commit -m "feat: drive the relevance gate off the series registry

Replace the flat teams/drivers/anchors keyword gate (which leaked
other-series content via shared manufacturer names) with registry-based
classification: keep iff a story classifies to a followed series. Migrate
GDELT, pipeline, and main off the removed cfg.keywords field."
```

---

### Task 3: Core-guaranteed selection (`select_digest`)

Add the pure selection function and wire it into `main.run` in place of the raw top-N slice.

**Files:**
- Modify: `digest/gate.py` (add `select_digest`)
- Modify: `digest/main.py:84` (call it)
- Test: `tests/test_gate.py`

**Interfaces:**
- Consumes: `ScoredStory` (has `.story.series` and `.buzz`), already sorted by buzz descending from `filter_stories`.
- Produces: `select_digest(survivors: list[ScoredStory], *, max_stories: int, core_series: set[str], core_floor: int) -> list[ScoredStory]` — at most `max_stories`, sorted by buzz descending, with a guaranteed floor of core-series stories.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_gate.py` (extend the existing `_scored` helper with a series arg):

```python
from digest.gate import filter_stories, select_digest


def _scored_series(key, buzz, series):
    story = Story(key=key, canonical_url=f"https://x/{key}", title=key, series=series, items=[])
    return ScoredStory(story=story, reddit_raw=0, breadth_raw=0, spike_raw=0, buzz=buzz)


CORE = {"f1", "indycar"}


def test_select_reserves_floor_for_core_over_higher_buzz_others():
    survivors = [
        _scored_series("o1", 0.9, "nascar"),
        _scored_series("o2", 0.8, "wec"),
        _scored_series("c1", 0.3, "f1"),
        _scored_series("c2", 0.2, "indycar"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=2)
    keys = [s.story.key for s in out]
    assert len(out) == 3
    assert "c1" in keys and "c2" in keys          # floor honored despite low buzz
    assert keys == ["o1", "c1", "c2"]             # sorted by buzz desc for display


def test_select_underfilled_floor_wastes_no_slot():
    survivors = [
        _scored_series("o1", 0.9, "nascar"),
        _scored_series("o2", 0.8, "wec"),
        _scored_series("c1", 0.5, "f1"),
        _scored_series("o3", 0.4, "imsa"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=2)
    assert [s.story.key for s in out] == ["o1", "o2", "c1"]   # only 1 core exists; fill by buzz


def test_select_high_buzz_core_may_exceed_floor():
    survivors = [
        _scored_series("c1", 0.9, "f1"),
        _scored_series("c2", 0.85, "indycar"),
        _scored_series("c3", 0.8, "f1"),
        _scored_series("o1", 0.7, "nascar"),
    ]
    out = select_digest(survivors, max_stories=3, core_series=CORE, core_floor=1)
    assert [s.story.key for s in out] == ["c1", "c2", "c3"]   # floor is a minimum, not a cap


def test_select_caps_at_max_stories():
    survivors = [_scored_series(f"s{i}", 1.0 - i / 100, "nascar") for i in range(20)]
    out = select_digest(survivors, max_stories=15, core_series=CORE, core_floor=6)
    assert len(out) == 15
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_gate.py -k select -v`
Expected: FAIL — `ImportError: cannot import name 'select_digest'`.

- [ ] **Step 3: Implement `select_digest` in `digest/gate.py`**

Append to `digest/gate.py`:

```python
def select_digest(survivors: list[ScoredStory], *, max_stories: int,
                  core_series: set[str], core_floor: int) -> list[ScoredStory]:
    """Pick the day's stories: reserve a floor of core-series slots, fill by buzz.

    `survivors` is already sorted by buzz descending. The floor is a minimum,
    not a cap — high-buzz core stories can occupy more than `core_floor` slots
    because they also compete in the general fill.
    """
    core = [s for s in survivors if s.story.series in core_series]
    guaranteed = core[:core_floor]
    guaranteed_ids = {id(s) for s in guaranteed}
    pool = [s for s in survivors if id(s) not in guaranteed_ids]
    fill = pool[: max(0, max_stories - len(guaranteed))]
    chosen = guaranteed + fill
    chosen.sort(key=lambda s: s.buzz, reverse=True)
    return chosen[:max_stories]
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_gate.py -v`
Expected: PASS — all gate tests.

- [ ] **Step 5: Wire into `main.run`**

In `digest/main.py`, update the import (line 14) and the selection line (84):

```python
from digest.gate import filter_stories, select_digest
```

```python
        top = select_digest(
            survivors, max_stories=cfg.max_stories,
            core_series=set(cfg.core_series), core_floor=cfg.core_floor,
        )
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: PASS — full suite green.

- [ ] **Step 7: Lint + commit**

```bash
uv run ruff format digest/gate.py digest/main.py tests/test_gate.py
uv run ruff check digest/gate.py digest/main.py tests/test_gate.py
git add digest/gate.py digest/main.py tests/test_gate.py
git commit -m "feat: core-guaranteed slot selection for the digest"
```

---

### Task 4: Populate real config (series blocks, max_stories=15, core settings)

Replace the `[keywords]` table in the live and example configs with the six `[[series]]` blocks and the core settings. This is the data that actually turns the feature on. Validated by loading the real file and a dry-run.

**Files:**
- Modify: `config.toml:9,53-63` (bump `max_stories`, replace `[keywords]` with `[[series]]` + core settings)
- Modify: `config.example.toml` (mirror the shape)
- Test: `tests/test_config.py` (load the real `config.toml`)

**Interfaces:**
- Consumes: everything from Tasks 1-3.

- [ ] **Step 1: Write a failing test that loads the real config**

Add to `tests/test_config.py`:

```python
def test_real_config_toml_has_series_registry():
    cfg = load_config("config.toml")
    ids = {s.id for s in cfg.series}
    assert {"f1", "indycar", "wec", "imsa", "nascar", "formulae"} <= ids
    assert cfg.max_stories == 15
    assert set(cfg.core_series) == {"f1", "indycar"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_config.py::test_real_config_toml_has_series_registry -v`
Expected: FAIL — real `config.toml` still has `[keywords]`, no `[[series]]`; `cfg.series` empty and `max_stories == 8`.

- [ ] **Step 3: Edit `config.toml`**

Set line 9 to `max_stories = 15` and add core settings beneath it:

```toml
max_stories = 15
core_series = ["f1", "indycar"]   # guaranteed floor of slots for these
core_floor = 6
```

Replace the entire `[keywords]` block (lines 53-63) with:

```toml
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
terms = ["Formula E", "E-Prix", "Gen3", "ABB FIA"]
```

Note: the `[keywords]` table used by GDELT is gone; GDELT reads its F1/IndyCar terms from the `f1`/`indycar` series blocks now.

- [ ] **Step 4: Mirror the change in `config.example.toml`**

Apply the same `max_stories`/`core_series`/`core_floor` and `[[series]]` structure to `config.example.toml`, replacing its `[keywords]` block. (If `config.example.toml` doesn't exist, create it as a copy of `config.toml` with the SES/secret values replaced by placeholders.)

- [ ] **Step 5: Run to verify pass + dry-run the pipeline**

Run: `uv run pytest tests/test_config.py -v`
Expected: PASS.

Run: `uv run python -m digest.main --dry-run`
Expected: prints "[dry-run] N stories would be sent" with N ≤ 15; scan the titles — WEC/IMSA/NASCAR/FE stories should now appear alongside F1/IndyCar, and the F1/IndyCar core should hold ≥ up-to-6 of the slots. No crash. (Requires network for RSS/GDELT; if offline, skip and note it.)

- [ ] **Step 6: Commit**

```bash
git add config.toml config.example.toml tests/test_config.py
git commit -m "feat: enable WEC/IMSA/NASCAR/Formula E; max_stories=15"
```

---

### Task 5: Documentation

Update the README and example config so the registry is the documented extension point (satisfies bean `qvrs`).

**Files:**
- Modify: `README.md`
- Test: none (docs)

**Interfaces:** none.

- [ ] **Step 1: Update `README.md`**

Add/adjust a "Configuration" (or "Series") section documenting:

- The `[[series]]` registry: `id`, `label`, `terms`; a story is kept iff its title matches a series' term (substring, case-insensitive), and registry order is match priority.
- `max_stories = 15`, `core_series`, `core_floor` — the core-guaranteed floor semantics (floor is a minimum, not a cap).
- **How to add a new series** (this is bean `qvrs`): add a `[[series]]` block with distinctive `terms` (series name, signature events, unambiguous driver/team names — avoid bare shared manufacturer names, which cause cross-series leakage); optionally add a feed with `series = "<id>"` to force-classify a dedicated source. No code change required.
- Note that GDELT's spike signal covers F1/IndyCar only; other series rank on social + breadth (spike defaults to neutral).

Update any existing README line that says the digest is "F1/IndyCar" to reflect the followed set, and any reference to the old `[keywords]` block.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: document the series registry and how to add a series"
```

- [ ] **Step 3: Close out the bean**

Mark the tracking bean's todos done and complete it (only if the dry-run in Task 4 confirmed the new series surface):

```bash
beans update daily-motorsports-digest-l2lf -s completed \
  --body-append "## Summary of Changes
Registry-based relevance gate (closes the shared-name leak), select_digest core-guaranteed floor, max_stories=15, and WEC/IMSA/NASCAR/Formula E enabled. GDELT stays F1/IndyCar-scoped for spikes. Docs updated (satisfies qvrs)."
```

Consider whether the child series beans (`a6b9` WEC, `xya5` IMSA, `r7sq` NASCAR, `1fe9` Formula E) and doc bean `qvrs` are now satisfied and can be closed too — offer that to the user rather than closing unilaterally.

---

## Self-Review

**Spec coverage:**
- Add WEC/IMSA/NASCAR/FE → Task 4 (config data) + Task 2 (gate keeps them). ✓
- Per-series registry replaces flat keywords → Task 1 (type) + Task 2 (gate). ✓
- Keep iff classifies to a followed series → Task 2 `is_relevant`/`normalize_items`. ✓
- Drop driver+anchor leak heuristic → Task 2 Step 3 (deleted). ✓
- max_stories=15 → Task 1 (default) + Task 4 (real config). ✓
- Core-guaranteed floor → Task 3 `select_digest`. ✓
- Config plumbing (SeriesDef, core_series, core_floor, remove keywords) → Task 1 + Task 2 Step 7. ✓
- Error handling (empty/malformed series, unknown core id, clamp floor) → Task 1 Step 4 (validation). Note: spec said "raise on empty series"; the plan raises on *unknown core id* and clamps floor, but treats empty series as legacy-permissive during migration (Tasks 1-3) and only becomes non-empty in Task 4. The real config always has series, so the operational guarantee holds. ✓
- Testing (leak regression, select_digest cases, config parsing) → Tasks 2, 3, 1/4. ✓
- Rollout note (calibration on) → covered by Task 4 dry-run. ✓
- Docs (README, example, qvrs) → Task 5. ✓
- GDELT interface collision (spec gap) → flagged in Global Constraints; handled in Task 2 Steps 4-5. ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code; README step lists concrete content rather than "document appropriately." ✓

**Type consistency:** `SeriesDef(id, label, terms: tuple[str,...])` used identically across config, normalize, gdelt, and tests. `classify_series`/`is_relevant`/`normalize_items`/`build_keyword_list`/`parse_articles`/`fetch_gdelt` all take `registry: tuple[SeriesDef, ...]` after Task 2. `select_digest` signature identical in gate.py, main.py, and tests. ✓
