# F1/IndyCar Morning Buzz Digest — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a daily Python job that emails a buzz-ranked recap of F1/IndyCar news, sourced from RSS + GDELT + Reddit, summarized by Haiku 4.5, and sent via Amazon SES.

**Architecture:** A seven-stage pipeline (collect → normalize → cluster → score → gate → summarize → send). Each stage is a pure function of the previous stage's output where possible, so stages are independently unit-testable and stages 1–5 can dry-run to a ranked list without sending. A SQLite state store enforces a cross-day suppress window. An orchestrator (`main.py`) wires the stages and is fired by a systemd timer on a Raspberry Pi at ~06:00 local.

**Tech Stack:** Python 3.11+, `praw` (Reddit), `gdeltdoc` (GDELT DOC 2.0), `feedparser` (RSS), `rapidfuzz` (fuzzy clustering), `boto3` (SES), `anthropic` (Haiku), `pytest` (tests).

## Global Constraints

- **Python 3.11+** (uses `X | Y` union syntax, `datetime.UTC`).
- **4-space indentation**, max line length 140 columns.
- **Summarizer model is `claude-haiku-4-5`** — never send `thinking` or `effort` params to it (unsupported on Haiku, and unneeded).
- **No article scraping** — summaries are built from titles + GDELT metadata + Reddit discussion only.
- **Secrets come from env / a git-ignored `.env`** — never hardcode credentials, never commit them.
- **12-factor config** — all tunables (weights, threshold, calibration flag, suppress window, escalation factor, keyword lists) come from config, not literals in logic.
- **Every git commit message** ends with the two trailers:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01SC99RPQqgiLcT37ayiRJgR
  ```
  (Omitted from the per-step commit commands below for brevity — append them to every commit.)
- **Tests never hit the network** — RSS/GDELT/Reddit/SES/Anthropic clients are faked or their parsing functions tested against fixture data.
- **Data model is the shared contract** — every stage consumes and produces the dataclasses defined in Task 1.

---

### Task 1: Project scaffolding, dependencies, config, and data models

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `digest/__init__.py`
- Create: `digest/models.py`
- Create: `digest/config.py`
- Create: `config.example.toml`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Produces: the shared dataclasses `RawItem`, `Story`, `ScoredStory`, `Blurb` (in `digest/models.py`), and `Config` + `load_config(path: str | None = None) -> Config` (in `digest/config.py`). Every later task consumes these.

- [ ] **Step 1: Create `requirements.txt`**

```
praw>=7.7
gdeltdoc>=1.5
feedparser>=6.0
rapidfuzz>=3.6
boto3>=1.34
anthropic>=0.40
```

- [ ] **Step 2: Create `pyproject.toml`**

```toml
[project]
name = "daily-motorsports-digest"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.setuptools.packages.find]
include = ["digest*"]
```

- [ ] **Step 3: Create `digest/__init__.py` and `tests/__init__.py`** (both empty)

```python
```

- [ ] **Step 4: Create `digest/models.py`**

```python
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RawItem:
    """A single item from one source before clustering."""
    source: str                       # "rss" | "gdelt" | "reddit"
    url: str
    title: str
    domain: str = ""
    published_at: datetime | None = None
    reddit_score: int = 0
    reddit_comments: int = 0
    series: str = ""                  # "f1" | "indycar" | ""
    extra: dict = field(default_factory=dict)


@dataclass
class Story:
    """A cluster of RawItems referring to the same event across sources."""
    key: str                          # canonical url + title hash
    canonical_url: str
    title: str
    series: str
    items: list[RawItem]

    @property
    def domains(self) -> set[str]:
        return {i.domain for i in self.items if i.domain}


@dataclass
class ScoredStory:
    story: Story
    reddit_raw: float
    breadth_raw: float
    spike_raw: float
    buzz: float = 0.0


@dataclass
class Blurb:
    scored: ScoredStory
    text: str
```

- [ ] **Step 5: Create `config.example.toml`**

```toml
# Copy to config.toml and fill in, or set the matching env vars.
model = "claude-haiku-4-5"
threshold = 0.0            # ignored while calibration = true
calibration = true         # send every day + log scores until tuned
suppress_days = 3
escalation_factor = 1.5
db_path = "state.db"
timezone = "America/New_York"
max_stories = 8

[weights]
reddit = 0.5
breadth = 0.35
spike = 0.15

[ses]
sender = "digest@example.com"
recipient = "you@example.com"
aws_region = "us-east-1"

[[rss_feeds]]
url = "https://www.autosport.com/rss/feed/all"
series = ""                # "" = classify each entry by title

[[rss_feeds]]
url = "https://www.the-race.com/feed/"
series = ""

[[rss_feeds]]
url = "https://www.motorsport.com/rss/all/news/"
series = ""

[[rss_feeds]]
url = "https://racer.com/feed/"
series = "indycar"

[[subreddits]]
name = "formula1"
series = "f1"

[[subreddits]]
name = "IndyCar"
series = "indycar"

[keywords]
series_f1 = ["Formula 1", "Formula One", "F1", "Grand Prix"]
series_indycar = ["IndyCar", "IndyCar Series", "Indy 500", "Indianapolis 500"]
teams = ["Red Bull", "Ferrari", "Mercedes", "McLaren", "Aston Martin",
         "Alpine", "Williams", "Racing Bulls", "Sauber", "Haas",
         "Penske", "Ganassi", "Andretti", "Arrow McLaren", "Rahal"]
drivers = ["Verstappen", "Hamilton", "Norris", "Leclerc", "Russell",
           "Piastri", "Sainz", "Alonso", "Palou", "Newgarden",
           "Dixon", "Herta", "O'Ward", "Power", "Rossi"]
anchors = ["Formula 1", "F1", "IndyCar", "Grand Prix", "racing",
           "motorsport", "qualifying", "podium", "circuit"]
```

- [ ] **Step 6: Create `.env.example`**

```
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=daily-motorsports-digest/0.1 by u_yourname
ANTHROPIC_API_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
```

- [ ] **Step 7: Write the failing test — `tests/test_config.py`**

```python
import textwrap

from digest.config import load_config


def test_load_config_reads_toml_and_env(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(textwrap.dedent("""
        model = "claude-haiku-4-5"
        threshold = 0.4
        calibration = false
        suppress_days = 3
        escalation_factor = 1.5
        db_path = "state.db"
        timezone = "America/New_York"
        max_stories = 8

        [weights]
        reddit = 0.5
        breadth = 0.35
        spike = 0.15

        [ses]
        sender = "d@example.com"
        recipient = "you@example.com"
        aws_region = "us-east-1"

        [[rss_feeds]]
        url = "https://example.com/feed"
        series = "indycar"

        [[subreddits]]
        name = "formula1"
        series = "f1"

        [keywords]
        series_f1 = ["F1"]
        series_indycar = ["IndyCar"]
        teams = ["Ferrari"]
        drivers = ["Verstappen"]
        anchors = ["racing"]
    """))
    monkeypatch.setenv("REDDIT_CLIENT_ID", "cid")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret")
    monkeypatch.setenv("REDDIT_USER_AGENT", "ua")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")

    cfg = load_config(str(cfg_file))

    assert cfg.model == "claude-haiku-4-5"
    assert cfg.calibration is False
    assert cfg.weights["breadth"] == 0.35
    assert cfg.escalation_factor == 1.5
    assert cfg.reddit_client_id == "cid"
    assert cfg.anthropic_api_key == "sk-ant"
    assert cfg.rss_feeds[0]["series"] == "indycar"
    assert cfg.subreddits[0]["name"] == "formula1"
    assert "Verstappen" in cfg.keywords["drivers"]


def test_load_config_defaults_when_calibration_true(tmp_path):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        'calibration = true\n[ses]\nsender="a"\nrecipient="b"\naws_region="us-east-1"\n'
    )
    cfg = load_config(str(cfg_file))
    assert cfg.calibration is True
    assert cfg.model == "claude-haiku-4-5"      # default
    assert cfg.suppress_days == 3               # default
```

- [ ] **Step 8: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.config'`

- [ ] **Step 9: Create `digest/config.py`**

```python
import os
import tomllib
from dataclasses import dataclass, field


@dataclass
class Config:
    model: str = "claude-haiku-4-5"
    threshold: float = 0.0
    calibration: bool = True
    suppress_days: int = 3
    escalation_factor: float = 1.5
    db_path: str = "state.db"
    timezone: str = "America/New_York"
    max_stories: int = 8
    weights: dict = field(default_factory=lambda: {"reddit": 0.5, "breadth": 0.35, "spike": 0.15})
    ses_sender: str = ""
    ses_recipient: str = ""
    aws_region: str = "us-east-1"
    rss_feeds: list = field(default_factory=list)
    subreddits: list = field(default_factory=list)
    keywords: dict = field(default_factory=dict)
    # Secrets (from env)
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = ""
    anthropic_api_key: str = ""


def load_config(path: str | None = None) -> Config:
    """Load config from a TOML file (path or ./config.toml) plus secrets from env."""
    path = path or "config.toml"
    with open(path, "rb") as fh:
        data = tomllib.load(fh)

    ses = data.get("ses", {})
    cfg = Config(
        model=data.get("model", "claude-haiku-4-5"),
        threshold=float(data.get("threshold", 0.0)),
        calibration=bool(data.get("calibration", True)),
        suppress_days=int(data.get("suppress_days", 3)),
        escalation_factor=float(data.get("escalation_factor", 1.5)),
        db_path=data.get("db_path", "state.db"),
        timezone=data.get("timezone", "America/New_York"),
        max_stories=int(data.get("max_stories", 8)),
        weights=data.get("weights", {"reddit": 0.5, "breadth": 0.35, "spike": 0.15}),
        ses_sender=ses.get("sender", ""),
        ses_recipient=ses.get("recipient", ""),
        aws_region=ses.get("aws_region", "us-east-1"),
        rss_feeds=data.get("rss_feeds", []),
        subreddits=data.get("subreddits", []),
        keywords=data.get("keywords", {}),
        reddit_client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
        reddit_client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
        reddit_user_agent=os.environ.get("REDDIT_USER_AGENT", ""),
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    return cfg
```

- [ ] **Step 10: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 11: Commit**

```bash
git add requirements.txt pyproject.toml .env.example config.example.toml \
        digest/ tests/
git commit -m "feat: scaffold project with config loader and data models"
```

---

### Task 2: URL normalization and series classification

**Files:**
- Create: `digest/normalize.py`
- Create: `tests/test_normalize.py`

**Interfaces:**
- Consumes: `RawItem` (Task 1).
- Produces:
  - `canonicalize_url(url: str) -> str`
  - `classify_series(title: str, source_series: str, keywords: dict) -> str`
  - `normalize_items(items: list[RawItem], keywords: dict) -> list[RawItem]`

- [ ] **Step 1: Write the failing test — `tests/test_normalize.py`**

```python
from digest.models import RawItem
from digest.normalize import canonicalize_url, classify_series, normalize_items

KEYWORDS = {
    "series_f1": ["Formula 1", "F1", "Grand Prix"],
    "series_indycar": ["IndyCar", "Indy 500"],
    "teams": ["Ferrari", "Penske"],
    "drivers": ["Verstappen", "Palou"],
}


def test_canonicalize_strips_tracking_and_fragment():
    dirty = "HTTPS://www.Autosport.com/f1/news/story/?utm_source=x&fbclid=y&id=5#top"
    assert canonicalize_url(dirty) == "https://www.autosport.com/f1/news/story/?id=5"


def test_canonicalize_normalizes_amp_and_trailing_slash():
    assert canonicalize_url("https://example.com/a/amp/") == "https://example.com/a"


def test_classify_series_prefers_source_hint():
    assert classify_series("Some ambiguous headline", "indycar", KEYWORDS) == "indycar"


def test_classify_series_from_title_keywords():
    assert classify_series("Verstappen wins the Grand Prix", "", KEYWORDS) == "f1"
    assert classify_series("Palou dominates at Indy 500", "", KEYWORDS) == "indycar"
    assert classify_series("Unrelated tech news", "", KEYWORDS) == ""


def test_normalize_items_sets_domain_and_series():
    item = RawItem(source="rss", url="https://www.autosport.com/f1/?utm_source=z",
                   title="Ferrari upgrade for the Grand Prix")
    out = normalize_items([item], KEYWORDS)[0]
    assert out.url == "https://www.autosport.com/f1/"
    assert out.domain == "www.autosport.com"
    assert out.series == "f1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_normalize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.normalize'`

- [ ] **Step 3: Create `digest/normalize.py`**

```python
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from digest.models import RawItem

_TRACKING_PREFIXES = ("utm_",)
_TRACKING_KEYS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "cmpid"}


def canonicalize_url(url: str) -> str:
    """Lowercase host, strip tracking params + fragment, normalize AMP + trailing slash."""
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()

    path = parsed.path
    if path.endswith("/amp/"):
        path = path[:-5]
    elif path.endswith("/amp"):
        path = path[:-4]
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")

    kept = [(k, v) for k, v in parse_qsl(parsed.query)
            if not k.startswith(_TRACKING_PREFIXES) and k not in _TRACKING_KEYS]
    query = urlencode(kept)

    return urlunparse((scheme, netloc, path, "", query, ""))


def classify_series(title: str, source_series: str, keywords: dict) -> str:
    """Return 'f1' | 'indycar' | '' — source hint wins, else classify from title."""
    if source_series:
        return source_series
    low = title.lower()
    if any(k.lower() in low for k in keywords.get("series_indycar", [])):
        return "indycar"
    if any(k.lower() in low for k in keywords.get("series_f1", [])):
        return "f1"
    return ""


def normalize_items(items: list[RawItem], keywords: dict) -> list[RawItem]:
    """Return new items with canonical URL, extracted domain, and resolved series."""
    out = []
    for it in items:
        url = canonicalize_url(it.url)
        domain = urlparse(url).netloc
        series = classify_series(it.title, it.series, keywords)
        out.append(RawItem(
            source=it.source, url=url, title=it.title.strip(), domain=domain,
            published_at=it.published_at, reddit_score=it.reddit_score,
            reddit_comments=it.reddit_comments, series=series, extra=it.extra,
        ))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_normalize.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/normalize.py tests/test_normalize.py
git commit -m "feat: add URL canonicalization and series classification"
```

---

### Task 3: Clustering (dedup)

**Files:**
- Create: `digest/cluster.py`
- Create: `tests/test_cluster.py`

**Interfaces:**
- Consumes: normalized `RawItem` list (Task 2), `Story` (Task 1).
- Produces:
  - `story_key(canonical_url: str, title: str) -> str`
  - `cluster_items(items: list[RawItem], title_threshold: int = 88) -> list[Story]`

- [ ] **Step 1: Write the failing test — `tests/test_cluster.py`**

```python
from digest.cluster import cluster_items, story_key
from digest.models import RawItem


def _item(source, url, title, domain, series="f1", score=0, comments=0):
    return RawItem(source=source, url=url, title=title, domain=domain,
                   series=series, reddit_score=score, reddit_comments=comments)


def test_story_key_is_stable_and_url_dependent():
    a = story_key("https://x.com/a", "Some Title")
    b = story_key("https://x.com/a", "Some Title")
    c = story_key("https://x.com/b", "Some Title")
    assert a == b
    assert a != c


def test_same_url_across_sources_clusters_into_one_story():
    items = [
        _item("rss", "https://autosport.com/story", "Verstappen wins", "autosport.com"),
        _item("reddit", "https://autosport.com/story", "Verstappen wins", "reddit.com",
              score=4200, comments=900),
    ]
    stories = cluster_items(items)
    assert len(stories) == 1
    assert len(stories[0].items) == 2


def test_fuzzy_title_match_clusters_syndicated_versions():
    items = [
        _item("rss", "https://autosport.com/a", "Verstappen to Mercedes rumor resurfaces", "autosport.com"),
        _item("rss", "https://motorsport.com/b", "Verstappen to Mercedes rumour resurfaces", "motorsport.com"),
    ]
    stories = cluster_items(items)
    assert len(stories) == 1
    assert stories[0].domains == {"autosport.com", "motorsport.com"}


def test_distinct_stories_stay_separate():
    items = [
        _item("rss", "https://a.com/1", "Iowa doubleheader preview", "a.com"),
        _item("rss", "https://b.com/2", "Verstappen wins in Austria", "b.com"),
    ]
    stories = cluster_items(items)
    assert len(stories) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_cluster.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.cluster'`

- [ ] **Step 3: Create `digest/cluster.py`**

```python
import hashlib

from rapidfuzz import fuzz

from digest.models import RawItem, Story


def story_key(canonical_url: str, title: str) -> str:
    """Stable identity for a story: canonical URL + a short hash of the title."""
    h = hashlib.sha1(title.strip().lower().encode("utf-8")).hexdigest()[:10]
    return f"{canonical_url}#{h}"


def cluster_items(items: list[RawItem], title_threshold: int = 88) -> list[Story]:
    """Group items into stories by canonical-URL match OR fuzzy title match."""
    clusters: list[list[RawItem]] = []
    for it in items:
        placed = False
        for cluster in clusters:
            head = cluster[0]
            if it.url == head.url or fuzz.token_sort_ratio(it.title, head.title) >= title_threshold:
                cluster.append(it)
                placed = True
                break
        if not placed:
            clusters.append([it])

    stories = []
    for cluster in clusters:
        head = cluster[0]
        series = _majority_series(cluster)
        stories.append(Story(
            key=story_key(head.url, head.title),
            canonical_url=head.url,
            title=head.title,
            series=series,
            items=cluster,
        ))
    return stories


def _majority_series(cluster: list[RawItem]) -> str:
    counts: dict[str, int] = {}
    for it in cluster:
        if it.series:
            counts[it.series] = counts.get(it.series, 0) + 1
    if not counts:
        return ""
    return max(counts, key=counts.get)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_cluster.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/cluster.py tests/test_cluster.py
git commit -m "feat: add story clustering by canonical URL and fuzzy title"
```

---

### Task 4: Scoring

**Files:**
- Create: `digest/score.py`
- Create: `tests/test_score.py`

**Interfaces:**
- Consumes: `Story` (Task 1).
- Produces:
  - `rank_normalize(values: list[float]) -> list[float]`
  - `score_stories(stories: list[Story], series_spike: dict[str, float], weights: dict[str, float]) -> list[ScoredStory]` — returns a list sorted by `buzz` descending.

- [ ] **Step 1: Write the failing test — `tests/test_score.py`**

```python
from digest.models import RawItem, Story
from digest.score import rank_normalize, score_stories

WEIGHTS = {"reddit": 0.5, "breadth": 0.35, "spike": 0.15}


def test_rank_normalize_maps_to_zero_one():
    assert rank_normalize([10, 20, 30]) == [0.0, 0.5, 1.0]


def test_rank_normalize_handles_single_value():
    assert rank_normalize([42]) == [1.0]


def test_rank_normalize_handles_empty():
    assert rank_normalize([]) == []


def _story(key, series, domains, reddit_score, reddit_comments):
    items = [RawItem(source="rss", url=f"https://{d}/x", title=key, domain=d, series=series)
             for d in domains]
    items[0].reddit_score = reddit_score
    items[0].reddit_comments = reddit_comments
    return Story(key=key, canonical_url=f"https://{domains[0]}/x", title=key,
                 series=series, items=items)


def test_score_stories_ranks_by_buzz_and_sorts_desc():
    big = _story("big", "f1", ["a.com", "b.com", "c.com"], 5000, 900)
    small = _story("small", "indycar", ["d.com"], 50, 5)
    spike = {"f1": 2.0, "indycar": 1.0}

    scored = score_stories([small, big], spike, WEIGHTS)

    assert [s.story.key for s in scored] == ["big", "small"]   # sorted desc
    assert scored[0].buzz > scored[1].buzz
    assert 0.0 <= scored[1].buzz <= 1.0


def test_score_uses_series_spike_lookup():
    s = _story("s", "f1", ["a.com"], 100, 10)
    scored = score_stories([s], {"f1": 3.0}, WEIGHTS)
    assert scored[0].spike_raw == 3.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_score.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.score'`

- [ ] **Step 3: Create `digest/score.py`**

```python
from digest.models import ScoredStory, Story


def rank_normalize(values: list[float]) -> list[float]:
    """Map values to 0..1 by rank within the pool. Ties share the same rank position."""
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [1.0]
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    for position, idx in enumerate(order):
        ranks[idx] = position / (n - 1)
    return ranks


def _reddit_signal(story: Story) -> float:
    return float(sum(i.reddit_score + i.reddit_comments for i in story.items))


def score_stories(stories: list[Story], series_spike: dict[str, float],
                  weights: dict[str, float]) -> list[ScoredStory]:
    """Rank-normalize each signal within the pool, then weighted-sum into buzz."""
    if not stories:
        return []

    reddit_raw = [_reddit_signal(s) for s in stories]
    breadth_raw = [float(len(s.domains)) for s in stories]
    spike_raw = [series_spike.get(s.series, 1.0) for s in stories]

    reddit_rank = rank_normalize(reddit_raw)
    breadth_rank = rank_normalize(breadth_raw)
    spike_rank = rank_normalize(spike_raw)

    scored = []
    for i, story in enumerate(stories):
        buzz = (weights["reddit"] * reddit_rank[i]
                + weights["breadth"] * breadth_rank[i]
                + weights["spike"] * spike_rank[i])
        scored.append(ScoredStory(
            story=story, reddit_raw=reddit_raw[i], breadth_raw=breadth_raw[i],
            spike_raw=spike_raw[i], buzz=buzz,
        ))
    scored.sort(key=lambda s: s.buzz, reverse=True)
    return scored
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_score.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/score.py tests/test_score.py
git commit -m "feat: add rank-normalized multi-signal buzz scoring"
```

---

### Task 5: SQLite state store

**Files:**
- Create: `digest/state.py`
- Create: `tests/test_state.py`

**Interfaces:**
- Produces:
  - `class StateStore` with:
    - `__init__(self, db_path: str)` — opens the DB and creates the schema if absent.
    - `last_sent(self, key: str, within_days: int) -> float | None` — returns the buzz score of the most recent send of `key` within the window, else `None`.
    - `record_sent(self, key: str, buzz: float, sent_at: datetime) -> None`
    - `close(self) -> None`

- [ ] **Step 1: Write the failing test — `tests/test_state.py`**

```python
from datetime import UTC, datetime, timedelta

from digest.state import StateStore


def test_unseen_key_returns_none(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    assert store.last_sent("k1", within_days=3) is None
    store.close()


def test_recorded_key_within_window_returns_buzz(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    now = datetime.now(UTC)
    store.record_sent("k1", 0.7, now)
    assert store.last_sent("k1", within_days=3) == 0.7
    store.close()


def test_key_outside_window_returns_none(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    old = datetime.now(UTC) - timedelta(days=5)
    store.record_sent("k1", 0.7, old)
    assert store.last_sent("k1", within_days=3) is None
    store.close()


def test_last_sent_returns_most_recent_score(tmp_path):
    store = StateStore(str(tmp_path / "s.db"))
    now = datetime.now(UTC)
    store.record_sent("k1", 0.4, now - timedelta(days=2))
    store.record_sent("k1", 0.9, now)
    assert store.last_sent("k1", within_days=3) == 0.9
    store.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_state.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.state'`

- [ ] **Step 3: Create `digest/state.py`**

```python
import sqlite3
from datetime import UTC, datetime, timedelta


class StateStore:
    """SQLite record of sent stories, for the cross-day suppress window."""

    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_stories (
                story_key TEXT NOT NULL,
                buzz_score REAL NOT NULL,
                sent_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def last_sent(self, key: str, within_days: int) -> float | None:
        cutoff = (datetime.now(UTC) - timedelta(days=within_days)).isoformat()
        row = self.conn.execute(
            "SELECT buzz_score FROM sent_stories "
            "WHERE story_key = ? AND sent_at >= ? "
            "ORDER BY sent_at DESC LIMIT 1",
            (key, cutoff),
        ).fetchone()
        return row[0] if row else None

    def record_sent(self, key: str, buzz: float, sent_at: datetime) -> None:
        self.conn.execute(
            "INSERT INTO sent_stories (story_key, buzz_score, sent_at) VALUES (?, ?, ?)",
            (key, buzz, sent_at.isoformat()),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_state.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/state.py tests/test_state.py
git commit -m "feat: add SQLite state store for sent-story history"
```

---

### Task 6: Gate (threshold + suppress window + escalation)

**Files:**
- Create: `digest/gate.py`
- Create: `tests/test_gate.py`

**Interfaces:**
- Consumes: `ScoredStory` (Task 1), `StateStore` (Task 5).
- Produces:
  - `filter_stories(scored: list[ScoredStory], state: StateStore, *, threshold: float, calibration: bool, suppress_days: int, escalation_factor: float) -> list[ScoredStory]`

- [ ] **Step 1: Write the failing test — `tests/test_gate.py`**

```python
from datetime import UTC, datetime

from digest.gate import filter_stories
from digest.models import ScoredStory, Story


def _scored(key, buzz):
    story = Story(key=key, canonical_url=f"https://x/{key}", title=key, series="f1", items=[])
    return ScoredStory(story=story, reddit_raw=0, breadth_raw=0, spike_raw=0, buzz=buzz)


class FakeState:
    def __init__(self, sent=None):
        self.sent = sent or {}          # key -> last buzz
        self.recorded = []

    def last_sent(self, key, within_days):
        return self.sent.get(key)

    def record_sent(self, key, buzz, sent_at):
        self.recorded.append((key, buzz))


def test_threshold_drops_low_scores_when_not_calibrating():
    scored = [_scored("hi", 0.8), _scored("lo", 0.2)]
    out = filter_stories(scored, FakeState(), threshold=0.5, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["hi"]


def test_calibration_ignores_threshold():
    scored = [_scored("lo", 0.1)]
    out = filter_stories(scored, FakeState(), threshold=0.9, calibration=True,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["lo"]


def test_recently_sent_story_is_suppressed():
    scored = [_scored("seen", 0.8)]
    state = FakeState(sent={"seen": 0.7})
    out = filter_stories(scored, state, threshold=0.5, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert out == []


def test_escalated_story_passes_suppression():
    scored = [_scored("seen", 0.8)]           # 0.8 > 0.5 * 1.5 = 0.75
    state = FakeState(sent={"seen": 0.5})
    out = filter_stories(scored, state, threshold=0.4, calibration=False,
                         suppress_days=3, escalation_factor=1.5)
    assert [s.story.key for s in out] == ["seen"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.gate'`

- [ ] **Step 3: Create `digest/gate.py`**

```python
from digest.models import ScoredStory


def filter_stories(scored: list[ScoredStory], state, *, threshold: float,
                   calibration: bool, suppress_days: int,
                   escalation_factor: float) -> list[ScoredStory]:
    """Drop below-threshold and recently-sent stories (unless escalated)."""
    survivors = []
    for s in scored:
        if not calibration and s.buzz < threshold:
            continue

        last = state.last_sent(s.story.key, suppress_days)
        if last is not None and s.buzz < last * escalation_factor:
            continue          # sent recently and not escalated → suppress

        survivors.append(s)
    return survivors
```

Note: escalation compares against the *last-sent* buzz, so a story that hasn't climbed by `escalation_factor` since its last send is suppressed. In calibration mode the threshold is skipped, but the suppress window still applies (we don't want duplicate emails even while calibrating).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gate.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/gate.py tests/test_gate.py
git commit -m "feat: add gate for threshold, suppress window, and escalation"
```

---

### Task 7: RSS collector

**Files:**
- Create: `digest/collect/__init__.py`
- Create: `digest/collect/rss.py`
- Create: `tests/test_rss.py`

**Interfaces:**
- Consumes: `RawItem` (Task 1).
- Produces:
  - `parse_feed(parsed, feed_series: str, since: datetime) -> list[RawItem]` — pure, takes a `feedparser`-parsed object.
  - `fetch_rss(feeds: list[dict], since: datetime) -> list[RawItem]` — calls `feedparser.parse` per feed URL, delegates to `parse_feed`.

- [ ] **Step 1: Create `digest/collect/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Write the failing test — `tests/test_rss.py`**

```python
from datetime import UTC, datetime, timezone
from types import SimpleNamespace

from digest.collect.rss import parse_feed


def _entry(title, link, published_struct):
    return SimpleNamespace(title=title, link=link, published_parsed=published_struct)


def test_parse_feed_keeps_recent_entries():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    recent = _entry("Verstappen wins", "https://autosport.com/a",
                    (2026, 7, 3, 8, 0, 0, 0, 0, 0))
    parsed = SimpleNamespace(entries=[recent])

    items = parse_feed(parsed, "f1", since)

    assert len(items) == 1
    assert items[0].source == "rss"
    assert items[0].title == "Verstappen wins"
    assert items[0].url == "https://autosport.com/a"
    assert items[0].series == "f1"


def test_parse_feed_drops_old_entries():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    old = _entry("Ancient news", "https://autosport.com/b",
                 (2026, 6, 1, 8, 0, 0, 0, 0, 0))
    parsed = SimpleNamespace(entries=[old])

    assert parse_feed(parsed, "f1", since) == []


def test_parse_feed_keeps_entry_with_no_date():
    since = datetime(2026, 7, 2, tzinfo=UTC)
    dateless = SimpleNamespace(title="No date", link="https://x/c", published_parsed=None)
    parsed = SimpleNamespace(entries=[dateless])

    items = parse_feed(parsed, "", since)
    assert len(items) == 1        # keep when we can't tell; downstream window filters
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_rss.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.collect.rss'`

- [ ] **Step 4: Create `digest/collect/rss.py`**

```python
import calendar
from datetime import UTC, datetime

import feedparser

from digest.models import RawItem


def _entry_datetime(entry) -> datetime | None:
    struct = getattr(entry, "published_parsed", None)
    if not struct:
        return None
    return datetime.fromtimestamp(calendar.timegm(struct), tz=UTC)


def parse_feed(parsed, feed_series: str, since: datetime) -> list[RawItem]:
    """Convert a feedparser result into RawItems within the window."""
    items = []
    for entry in parsed.entries:
        published = _entry_datetime(entry)
        if published is not None and published < since:
            continue
        items.append(RawItem(
            source="rss",
            url=getattr(entry, "link", ""),
            title=getattr(entry, "title", ""),
            published_at=published,
            series=feed_series,
        ))
    return items


def fetch_rss(feeds: list[dict], since: datetime) -> list[RawItem]:
    """Fetch and parse each configured RSS feed. Failures per feed are skipped."""
    items = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            items.extend(parse_feed(parsed, feed.get("series", ""), since))
        except Exception as exc:                    # noqa: BLE001 — one bad feed must not kill the run
            print(f"[rss] failed {feed.get('url')}: {exc}")
    return items
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_rss.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add digest/collect/__init__.py digest/collect/rss.py tests/test_rss.py
git commit -m "feat: add RSS collector"
```

---

### Task 8: GDELT collector

**Files:**
- Create: `digest/collect/gdelt.py`
- Create: `tests/test_gdelt.py`

**Interfaces:**
- Consumes: `RawItem` (Task 1).
- Produces:
  - `build_keyword_list(keywords: dict, kind: str) -> list[str]` — `kind` is `"f1"` or `"indycar"`; returns series + team + driver terms for that series.
  - `is_relevant(title: str, keywords: dict) -> bool` — enforces the co-term rule client-side.
  - `parse_articles(rows: list[dict], keywords: dict) -> list[RawItem]` — pure; filters by `is_relevant`.
  - `spike_ratio(volumes: list[float]) -> float` — last value / mean of prior values (default 1.0).
  - `fetch_gdelt(keywords: dict, since: datetime, end: datetime, client=None) -> tuple[list[RawItem], dict[str, float]]` — uses `gdeltdoc`; returns articles + `{"f1": ratio, "indycar": ratio}`.

**Note for the implementer:** `gdeltdoc` exposes `GdeltDoc().article_search(Filters(...))` → DataFrame (`url`, `title`, `seendate`, `domain`) and `timeline_search("timelinevol", Filters(...))` → DataFrame with a volume column. Column names have drifted across versions — verify against the installed `gdeltdoc` and the [gdeltdoc README](https://github.com/alex9smith/gdelt-doc-api) before wiring `fetch_gdelt`. The pure functions (`build_keyword_list`, `is_relevant`, `parse_articles`, `spike_ratio`) are what the tests cover; `fetch_gdelt` is thin glue over them.

- [ ] **Step 1: Write the failing test — `tests/test_gdelt.py`**

```python
from digest.collect.gdelt import (build_keyword_list, is_relevant, parse_articles, spike_ratio)

KEYWORDS = {
    "series_f1": ["Formula 1", "F1", "Grand Prix"],
    "series_indycar": ["IndyCar", "Indy 500"],
    "teams": ["Ferrari", "Penske"],
    "drivers": ["Verstappen", "Russell", "Palou"],
    "anchors": ["F1", "IndyCar", "racing", "Grand Prix"],
}


def test_build_keyword_list_scopes_to_series():
    f1 = build_keyword_list(KEYWORDS, "f1")
    assert "Formula 1" in f1 and "Ferrari" in f1 and "Verstappen" in f1
    assert "Indy 500" not in f1


def test_is_relevant_accepts_series_term():
    assert is_relevant("Ferrari's new F1 upgrade", KEYWORDS) is True


def test_is_relevant_requires_anchor_for_bare_driver_name():
    # "Russell" alone (a common surname) with no motorsport anchor → reject
    assert is_relevant("Senator Russell speaks on policy", KEYWORDS) is False
    # "Russell" WITH an anchor term → accept
    assert is_relevant("Russell fastest in F1 qualifying", KEYWORDS) is True


def test_parse_articles_filters_irrelevant():
    rows = [
        {"url": "https://a.com/1", "title": "Verstappen wins the Grand Prix", "domain": "a.com"},
        {"url": "https://b.com/2", "title": "Local news about a person named Norris", "domain": "b.com"},
    ]
    items = parse_articles(rows, KEYWORDS)
    assert [i.url for i in items] == ["https://a.com/1"]
    assert items[0].source == "gdelt"


def test_spike_ratio_computes_last_over_mean():
    assert spike_ratio([10, 10, 10, 30]) == 3.0
    assert spike_ratio([]) == 1.0
    assert spike_ratio([5]) == 1.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_gdelt.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.collect.gdelt'`

- [ ] **Step 3: Create `digest/collect/gdelt.py`**

```python
from datetime import datetime

from digest.models import RawItem


def build_keyword_list(keywords: dict, kind: str) -> list[str]:
    """Series + team + driver terms scoped to one series ('f1' or 'indycar')."""
    series_key = "series_f1" if kind == "f1" else "series_indycar"
    return (list(keywords.get(series_key, []))
            + list(keywords.get("teams", []))
            + list(keywords.get("drivers", [])))


def is_relevant(title: str, keywords: dict) -> bool:
    """Keep if the title has a series/team term, or a driver name WITH a motorsport anchor."""
    low = title.lower()
    series_terms = keywords.get("series_f1", []) + keywords.get("series_indycar", [])
    if any(t.lower() in low for t in series_terms + keywords.get("teams", [])):
        return True
    has_driver = any(d.lower() in low for d in keywords.get("drivers", []))
    has_anchor = any(a.lower() in low for a in keywords.get("anchors", []))
    return has_driver and has_anchor


def parse_articles(rows: list[dict], keywords: dict) -> list[RawItem]:
    """Convert GDELT article rows into relevant RawItems."""
    items = []
    for row in rows:
        title = row.get("title", "")
        if not is_relevant(title, keywords):
            continue
        items.append(RawItem(
            source="gdelt",
            url=row.get("url", ""),
            title=title,
            domain=row.get("domain", ""),
        ))
    return items


def spike_ratio(volumes: list[float]) -> float:
    """Last window's volume divided by the mean of prior windows. Default 1.0."""
    if len(volumes) < 2:
        return 1.0
    prior = volumes[:-1]
    mean_prior = sum(prior) / len(prior)
    if mean_prior == 0:
        return 1.0
    return volumes[-1] / mean_prior


def fetch_gdelt(keywords: dict, since: datetime, end: datetime, client=None):
    """Return (articles, {'f1': ratio, 'indycar': ratio}). Thin glue over the pure helpers.

    Verify gdeltdoc column names against the installed version before relying on this.
    """
    from gdeltdoc import Filters, GdeltDoc

    gd = client or GdeltDoc()
    fmt = "%Y-%m-%d"
    start_s, end_s = since.strftime(fmt), end.strftime(fmt)

    articles: list[RawItem] = []
    spikes: dict[str, float] = {}
    for kind in ("f1", "indycar"):
        try:
            filt = Filters(keyword=build_keyword_list(keywords, kind),
                           start_date=start_s, end_date=end_s, num_records=250)
            df = gd.article_search(filt)
            rows = df.to_dict("records") if df is not None and not df.empty else []
            articles.extend(parse_articles(rows, keywords))

            tl = gd.timeline_search("timelinevol", filt)
            vols = tl.iloc[:, -1].tolist() if tl is not None and not tl.empty else []
            spikes[kind] = spike_ratio([float(v) for v in vols])
        except Exception as exc:                    # noqa: BLE001 — one series must not kill the run
            print(f"[gdelt] failed {kind}: {exc}")
            spikes[kind] = 1.0
    return articles, spikes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_gdelt.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/collect/gdelt.py tests/test_gdelt.py
git commit -m "feat: add GDELT collector with client-side relevance filter and spike ratio"
```

---

### Task 9: Reddit collector

**Files:**
- Create: `digest/collect/reddit.py`
- Create: `tests/test_reddit.py`

**Interfaces:**
- Consumes: `RawItem` (Task 1).
- Produces:
  - `parse_submission(submission, series: str) -> RawItem` — pure; takes a PRAW-like submission object.
  - `fetch_reddit(reddit, subreddits: list[dict], limit: int = 50) -> list[RawItem]` — calls `reddit.subreddit(name).top(time_filter="day", limit=limit)`.

- [ ] **Step 1: Write the failing test — `tests/test_reddit.py`**

```python
from types import SimpleNamespace

from digest.collect.reddit import fetch_reddit, parse_submission


def _submission(title, url, score, comments, permalink="/r/formula1/abc"):
    return SimpleNamespace(title=title, url=url, score=score, num_comments=comments,
                           permalink=permalink)


def test_parse_submission_maps_fields():
    sub = _submission("Verstappen wins", "https://autosport.com/x", 4200, 900)
    item = parse_submission(sub, "f1")
    assert item.source == "reddit"
    assert item.url == "https://autosport.com/x"
    assert item.title == "Verstappen wins"
    assert item.reddit_score == 4200
    assert item.reddit_comments == 900
    assert item.series == "f1"


class FakeSubreddit:
    def __init__(self, subs):
        self._subs = subs

    def top(self, time_filter, limit):
        assert time_filter == "day"
        return self._subs[:limit]


class FakeReddit:
    def __init__(self, mapping):
        self._mapping = mapping

    def subreddit(self, name):
        return FakeSubreddit(self._mapping[name])


def test_fetch_reddit_pulls_each_configured_subreddit():
    reddit = FakeReddit({
        "formula1": [_submission("F1 story", "https://a/1", 100, 10)],
        "IndyCar": [_submission("Indy story", "https://b/2", 50, 5)],
    })
    subs = [{"name": "formula1", "series": "f1"}, {"name": "IndyCar", "series": "indycar"}]

    items = fetch_reddit(reddit, subs, limit=25)

    assert {i.series for i in items} == {"f1", "indycar"}
    assert len(items) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reddit.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.collect.reddit'`

- [ ] **Step 3: Create `digest/collect/reddit.py`**

```python
from digest.models import RawItem


def parse_submission(submission, series: str) -> RawItem:
    """Convert a PRAW submission into a RawItem."""
    return RawItem(
        source="reddit",
        url=submission.url,
        title=submission.title,
        reddit_score=int(submission.score),
        reddit_comments=int(submission.num_comments),
        series=series,
        extra={"permalink": f"https://reddit.com{submission.permalink}"},
    )


def fetch_reddit(reddit, subreddits: list[dict], limit: int = 50) -> list[RawItem]:
    """Pull top-of-day submissions from each configured subreddit."""
    items = []
    for sub in subreddits:
        try:
            for submission in reddit.subreddit(sub["name"]).top(time_filter="day", limit=limit):
                items.append(parse_submission(submission, sub.get("series", "")))
        except Exception as exc:                    # noqa: BLE001 — one subreddit must not kill the run
            print(f"[reddit] failed r/{sub.get('name')}: {exc}")
    return items
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_reddit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/collect/reddit.py tests/test_reddit.py
git commit -m "feat: add Reddit collector"
```

---

### Task 10: Summarization (Haiku)

**Files:**
- Create: `digest/summarize.py`
- Create: `tests/test_summarize.py`

**Interfaces:**
- Consumes: `ScoredStory` (Task 1), `Blurb` (Task 1).
- Produces:
  - `build_prompt(scored: list[ScoredStory]) -> str`
  - `parse_response(text: str, scored: list[ScoredStory]) -> list[Blurb]` — parses the model's JSON array and maps blurbs back to stories by index.
  - `summarize(client, scored: list[ScoredStory], model: str) -> list[Blurb]` — calls `client.messages.create(...)`; on failure falls back to the story title as the blurb text.

- [ ] **Step 1: Write the failing test — `tests/test_summarize.py`**

```python
import json
from types import SimpleNamespace

from digest.models import RawItem, ScoredStory, Story
from digest.summarize import build_prompt, parse_response, summarize


def _scored(title, score=100, comments=10, domains=("a.com",)):
    items = [RawItem(source="reddit", url="https://a/x", title=title, domain=domains[0],
                     reddit_score=score, reddit_comments=comments)]
    story = Story(key=title, canonical_url="https://a/x", title=title, series="f1", items=items)
    return ScoredStory(story=story, reddit_raw=score + comments,
                       breadth_raw=len(domains), spike_raw=1.0, buzz=0.9)


def test_build_prompt_includes_titles_and_indices():
    prompt = build_prompt([_scored("Verstappen wins"), _scored("Iowa preview")])
    assert "Verstappen wins" in prompt
    assert "Iowa preview" in prompt
    assert "0" in prompt and "1" in prompt


def test_parse_response_maps_json_back_to_stories():
    scored = [_scored("Verstappen wins"), _scored("Iowa preview")]
    text = json.dumps([
        {"index": 0, "blurb": "Max takes the win."},
        {"index": 1, "blurb": "Iowa doubleheader ahead."},
    ])
    blurbs = parse_response(text, scored)
    assert len(blurbs) == 2
    assert blurbs[0].text == "Max takes the win."
    assert blurbs[0].scored.story.title == "Verstappen wins"


def test_parse_response_tolerates_code_fenced_json():
    scored = [_scored("A story")]
    text = "```json\n[{\"index\": 0, \"blurb\": \"Blurb.\"}]\n```"
    blurbs = parse_response(text, scored)
    assert blurbs[0].text == "Blurb."


def test_summarize_falls_back_to_title_on_error():
    scored = [_scored("Fallback story")]

    class BoomClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                raise RuntimeError("api down")

    blurbs = summarize(BoomClient(), scored, model="claude-haiku-4-5")
    assert blurbs[0].text == "Fallback story"


def test_summarize_uses_client_response():
    scored = [_scored("Real story")]
    payload = json.dumps([{"index": 0, "blurb": "Generated blurb."}])

    class FakeClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                return SimpleNamespace(content=[SimpleNamespace(text=payload)])

    blurbs = summarize(FakeClient(), scored, model="claude-haiku-4-5")
    assert blurbs[0].text == "Generated blurb."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.summarize'`

- [ ] **Step 3: Create `digest/summarize.py`**

```python
import json
import re

from digest.models import Blurb, ScoredStory

_SYSTEM = (
    "You write concise motorsport news blurbs. For each story you are given a "
    "headline, its sources, and Reddit discussion stats. Write a punchy 2-3 "
    "sentence blurb per story capturing what happened and why it's buzzing. "
    "Do not invent facts beyond the headline and stats. Respond with ONLY a JSON "
    "array of objects: [{\"index\": <int>, \"blurb\": <string>}]."
)


def build_prompt(scored: list[ScoredStory]) -> str:
    lines = []
    for i, s in enumerate(scored):
        story = s.story
        domains = ", ".join(sorted(story.domains)) or "n/a"
        lines.append(
            f"[{i}] {story.title}\n"
            f"    sources: {domains}\n"
            f"    reddit: {int(s.reddit_raw)} (score+comments) across "
            f"{int(s.breadth_raw)} outlets"
        )
    return "Stories:\n\n" + "\n\n".join(lines)


def parse_response(text: str, scored: list[ScoredStory]) -> list[Blurb]:
    """Parse the model's JSON array and map blurbs to stories by index."""
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    data = json.loads(cleaned)
    by_index = {int(o["index"]): o["blurb"] for o in data}
    blurbs = []
    for i, s in enumerate(scored):
        blurbs.append(Blurb(scored=s, text=by_index.get(i, s.story.title)))
    return blurbs


def summarize(client, scored: list[ScoredStory], model: str) -> list[Blurb]:
    """Call Haiku to write blurbs; fall back to story titles on any failure."""
    if not scored:
        return []
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1500,
            system=_SYSTEM,
            messages=[{"role": "user", "content": build_prompt(scored)}],
        )
        return parse_response(response.content[0].text, scored)
    except Exception as exc:                        # noqa: BLE001 — degrade to titles, never crash the run
        print(f"[summarize] failed, using titles: {exc}")
        return [Blurb(scored=s, text=s.story.title) for s in scored]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_summarize.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/summarize.py tests/test_summarize.py
git commit -m "feat: add Haiku summarization with title fallback"
```

---

### Task 11: Email rendering and SES send

**Files:**
- Create: `digest/email.py`
- Create: `tests/test_email.py`

**Interfaces:**
- Consumes: `Blurb` (Task 1).
- Produces:
  - `render_subject(date) -> str`
  - `render_html(blurbs: list[Blurb], date) -> str`
  - `send_email(ses_client, sender: str, recipient: str, subject: str, html: str) -> None` — calls `ses_client.send_email(...)`.

- [ ] **Step 1: Write the failing test — `tests/test_email.py`**

```python
from datetime import date
from unittest.mock import MagicMock

from digest.email import render_html, render_subject, send_email
from digest.models import Blurb, RawItem, ScoredStory, Story


def _blurb(title, text, score, comments, domains):
    items = [RawItem(source="rss", url=f"https://{domains[0]}/x", title=title, domain=domains[0],
                     reddit_score=score, reddit_comments=comments)]
    story = Story(key=title, canonical_url=f"https://{domains[0]}/x", title=title,
                  series="f1", items=items)
    scored = ScoredStory(story=story, reddit_raw=score + comments,
                         breadth_raw=len(domains), spike_raw=1.0, buzz=0.9)
    return Blurb(scored=scored, text=text)


def test_render_subject_includes_date():
    assert "2026" in render_subject(date(2026, 7, 3))


def test_render_html_lists_blurbs_with_links_and_stats():
    blurbs = [_blurb("Verstappen wins", "Max takes it.", 4200, 900, ["autosport.com", "b.com"])]
    html = render_html(blurbs, date(2026, 7, 3))
    assert "Verstappen wins" in html
    assert "Max takes it." in html
    assert "https://autosport.com/x" in html
    assert "5100" in html or "4200" in html          # buzz stat present
    assert "2 outlets" in html


def test_send_email_calls_ses_with_expected_args():
    ses = MagicMock()
    send_email(ses, "d@example.com", "you@example.com", "Subject", "<p>hi</p>")
    ses.send_email.assert_called_once()
    kwargs = ses.send_email.call_args.kwargs
    assert kwargs["Source"] == "d@example.com"
    assert kwargs["Destination"]["ToAddresses"] == ["you@example.com"]
    assert kwargs["Message"]["Subject"]["Data"] == "Subject"
    assert kwargs["Message"]["Body"]["Html"]["Data"] == "<p>hi</p>"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_email.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.email'`

- [ ] **Step 3: Create `digest/email.py`**

```python
import html as html_lib

from digest.models import Blurb


def render_subject(date) -> str:
    return f"🏎️ Morning Buzz — {date:%a %b %-d, %Y}"


def _story_link(blurb: Blurb) -> str:
    return blurb.scored.story.canonical_url


def render_html(blurbs: list[Blurb], date) -> str:
    rows = []
    for n, blurb in enumerate(blurbs, start=1):
        s = blurb.scored
        title = html_lib.escape(s.story.title)
        text = html_lib.escape(blurb.text)
        link = html_lib.escape(_story_link(blurb))
        engagement = int(s.reddit_raw)
        outlets = int(s.breadth_raw)
        rows.append(
            f'<li style="margin-bottom:18px;">'
            f'<div style="font-weight:600;">{n}. {title}</div>'
            f'<div style="margin:4px 0;">{text}</div>'
            f'<div style="font-size:12px;color:#666;">'
            f'<a href="{link}">source</a> · {engagement} upvotes+comments · {outlets} outlets'
            f'</div></li>'
        )
    body = "\n".join(rows)
    return (
        f'<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px;">'
        f'<h2>🏎️ Morning Buzz — {date:%a %b %-d, %Y}</h2>'
        f'<ol style="list-style:none;padding-left:0;">{body}</ol>'
        f'</div>'
    )


def send_email(ses_client, sender: str, recipient: str, subject: str, html: str) -> None:
    ses_client.send_email(
        Source=sender,
        Destination={"ToAddresses": [recipient]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": html}},
        },
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_email.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add digest/email.py tests/test_email.py
git commit -m "feat: add HTML email rendering and SES send"
```

---

### Task 12: Orchestrator (`main.py`) with `--dry-run`

**Files:**
- Create: `digest/pipeline.py`
- Create: `digest/main.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything from Tasks 1–11.
- Produces:
  - `rank(raw_items: list[RawItem], series_spike: dict[str, float], state, cfg) -> list[ScoredStory]` (in `digest/pipeline.py`) — the pure normalize → cluster → score → gate chain. Testable without any network or clients.
  - `digest/main.py` with a CLI: `python -m digest.main [--dry-run] [--config PATH]`.

**Rationale:** the pure ranking chain lives in `pipeline.py` so it can be tested end-to-end with fixtures; `main.py` is thin glue (build clients, collect, call `rank`, then summarize/send or print).

- [ ] **Step 1: Write the failing test — `tests/test_pipeline.py`**

```python
from datetime import UTC, datetime

from digest.config import Config
from digest.models import RawItem
from digest.pipeline import rank


class FakeState:
    def last_sent(self, key, within_days):
        return None

    def record_sent(self, *a):
        pass


def _cfg():
    return Config(
        calibration=True, suppress_days=3, escalation_factor=1.5,
        weights={"reddit": 0.5, "breadth": 0.35, "spike": 0.15},
        keywords={"series_f1": ["F1", "Grand Prix"], "series_indycar": ["IndyCar"],
                  "teams": [], "drivers": [], "anchors": []},
    )


def test_rank_normalizes_clusters_scores_and_orders():
    raw = [
        RawItem(source="rss", url="https://autosport.com/a?utm_source=x",
                title="Verstappen to Mercedes rumor resurfaces", series="f1"),
        RawItem(source="rss", url="https://motorsport.com/b",
                title="Verstappen to Mercedes rumour resurfaces", series="f1"),
        RawItem(source="reddit", url="https://autosport.com/a",
                title="Verstappen to Mercedes rumor resurfaces", series="f1",
                reddit_score=5000, reddit_comments=900),
        RawItem(source="rss", url="https://racer.com/c",
                title="Iowa doubleheader preview", series="indycar"),
    ]
    scored = rank(raw, {"f1": 2.0, "indycar": 1.0}, FakeState(), _cfg())

    # The three Verstappen items collapse to one story; two stories total.
    assert len(scored) == 2
    assert scored[0].story.title.startswith("Verstappen")     # highest buzz first
    assert scored[0].breadth_raw >= 2                          # merged across domains


def test_rank_gate_suppresses_recently_sent():
    class SuppressState:
        def last_sent(self, key, within_days):
            return 1.0        # already sent high; nothing escalates past 1.0 * 1.5
        def record_sent(self, *a):
            pass

    raw = [RawItem(source="rss", url="https://a/x", title="F1 news", series="f1")]
    cfg = _cfg()
    cfg.calibration = False
    cfg.threshold = 0.0
    scored = rank(raw, {"f1": 1.0}, SuppressState(), cfg)
    assert scored == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.pipeline'`

- [ ] **Step 3: Create `digest/pipeline.py`**

```python
from digest.cluster import cluster_items
from digest.config import Config
from digest.gate import filter_stories
from digest.models import RawItem, ScoredStory
from digest.normalize import normalize_items
from digest.score import score_stories


def rank(raw_items: list[RawItem], series_spike: dict[str, float],
         state, cfg: Config) -> list[ScoredStory]:
    """Pure chain: normalize → cluster → score → gate. Returns surviving scored stories."""
    normalized = normalize_items(raw_items, cfg.keywords)
    stories = cluster_items(normalized)
    scored = score_stories(stories, series_spike, cfg.weights)
    return filter_stories(
        scored, state,
        threshold=cfg.threshold, calibration=cfg.calibration,
        suppress_days=cfg.suppress_days, escalation_factor=cfg.escalation_factor,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Create `digest/main.py`** (no unit test — thin glue; exercised manually and via `--dry-run`)

```python
import argparse
from datetime import UTC, date, datetime, timedelta

import anthropic
import boto3
import praw

from digest.collect.gdelt import fetch_gdelt
from digest.collect.reddit import fetch_reddit
from digest.collect.rss import fetch_rss
from digest.config import load_config
from digest.email import render_html, render_subject, send_email
from digest.pipeline import rank
from digest.state import StateStore
from digest.summarize import summarize


def _collect(cfg, since, end):
    """Gather raw items from all three sources plus GDELT spike ratios."""
    items = []
    items += fetch_rss(cfg.rss_feeds, since)

    gdelt_items, spikes = fetch_gdelt(cfg.keywords, since, end)
    items += gdelt_items

    reddit = praw.Reddit(client_id=cfg.reddit_client_id,
                         client_secret=cfg.reddit_client_secret,
                         user_agent=cfg.reddit_user_agent)
    items += fetch_reddit(reddit, cfg.subreddits)

    return items, spikes


def run(config_path: str | None, dry_run: bool) -> None:
    cfg = load_config(config_path)
    end = datetime.now(UTC)
    since = end - timedelta(days=1)

    state = StateStore(cfg.db_path)
    try:
        raw, spikes = _collect(cfg, since, end)
        scored = rank(raw, spikes, state, cfg)
        top = scored[: cfg.max_stories]

        if not top:
            print(f"[digest] nothing cleared the gate (top buzz: "
                  f"{scored[0].buzz:.3f} of {len(scored)})" if scored
                  else "[digest] no stories at all — no email sent")
            return

        if cfg.calibration:
            print("[calibration] day's scores: "
                  + ", ".join(f"{s.buzz:.3f}" for s in scored[:20]))

        if dry_run:
            print(f"[dry-run] {len(top)} stories would be sent:")
            for n, s in enumerate(top, 1):
                print(f"  {n}. [{s.buzz:.3f}] {s.story.title}  ({len(s.story.domains)} outlets)")
            return

        client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        blurbs = summarize(client, top, cfg.model)

        today = date.today()
        html = render_html(blurbs, today)
        ses = boto3.client("ses", region_name=cfg.aws_region)
        send_email(ses, cfg.ses_sender, cfg.ses_recipient, render_subject(today), html)

        for s in top:
            state.record_sent(s.story.key, s.buzz, end)
        print(f"[digest] sent {len(top)} stories")
    finally:
        state.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="F1/IndyCar morning buzz digest")
    parser.add_argument("--config", default=None, help="path to config.toml")
    parser.add_argument("--dry-run", action="store_true",
                        help="rank and print, but don't summarize or send")
    args = parser.parse_args()
    run(args.config, args.dry_run)


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS (all tests from Tasks 1–12 green)

- [ ] **Step 7: Commit**

```bash
git add digest/pipeline.py digest/main.py tests/test_pipeline.py
git commit -m "feat: add ranking pipeline and orchestrator CLI with --dry-run"
```

---

### Task 13: Deployment (systemd timer) and README

**Files:**
- Create: `deploy/motorsports-digest.service`
- Create: `deploy/motorsports-digest.timer`
- Create: `README.md`

**Interfaces:** none (deployment assets + docs).

- [ ] **Step 1: Create `deploy/motorsports-digest.service`**

```ini
[Unit]
Description=F1/IndyCar morning buzz digest
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/home/pi/daily-motorsports-digest
EnvironmentFile=/home/pi/daily-motorsports-digest/.env
ExecStart=/home/pi/daily-motorsports-digest/.venv/bin/python -m digest.main --config /home/pi/daily-motorsports-digest/config.toml
```

- [ ] **Step 2: Create `deploy/motorsports-digest.timer`**

```ini
[Unit]
Description=Run the motorsports digest every morning

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Create `README.md`**

```markdown
# Daily Motorsports Digest

A daily job that emails a buzz-ranked recap of F1/IndyCar news, sourced from
RSS + GDELT + Reddit, summarized by Claude Haiku 4.5, and sent via Amazon SES.
No email on genuinely slow news days.

See `docs/superpowers/specs/2026-07-03-motorsports-digest-design.md` for the
full design.

## Setup

1. **Python 3.11+.** Create a venv and install deps:
   ```bash
   python3.11 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
2. **Config:** copy and edit the templates:
   ```bash
   cp config.example.toml config.toml
   cp .env.example .env
   ```
   Fill in SES sender/recipient, keyword lists, and (in `.env`) Reddit +
   Anthropic + AWS credentials. `.env` and `config.toml` are git-ignored.
3. **Reddit app:** register a *script*-type app at
   <https://www.reddit.com/prefs/apps> to get `REDDIT_CLIENT_ID` /
   `REDDIT_CLIENT_SECRET`. Free tier (100 QPM) is fine for personal use.
4. **SES:** verify the sender (and, in sandbox mode, the recipient) address in
   the AWS SES console for your region.

## Run

```bash
# Rank and print the day's stories without summarizing or sending:
.venv/bin/python -m digest.main --dry-run

# Full run (summarize + email):
.venv/bin/python -m digest.main
```

## Calibration

Ships with `calibration = true` in `config.toml`. For the first ~2 weeks it
sends every day regardless of score and logs the day's buzz distribution. Watch
the `[calibration]` log lines, then pick a `threshold` from the observed scores,
set `calibration = false`, and the "no slow-news-day emails" behavior activates.

## Deploy on a Raspberry Pi (systemd timer)

```bash
sudo cp deploy/motorsports-digest.service /etc/systemd/system/
sudo cp deploy/motorsports-digest.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now motorsports-digest.timer
```

Adjust the paths/user in the unit files if you didn't clone to
`/home/pi/daily-motorsports-digest`. Inspect runs with:
```bash
systemctl status motorsports-digest.timer
journalctl -u motorsports-digest.service -n 50
```

## Tests

```bash
.venv/bin/python -m pytest -v
```
```

- [ ] **Step 4: Verify the suite still passes and the CLI imports**

Run: `python -m pytest -v && python -m digest.main --help`
Expected: all tests PASS; `--help` prints usage with `--dry-run` and `--config`.

- [ ] **Step 5: Commit**

```bash
git add deploy/ README.md
git commit -m "docs: add systemd deployment units and README"
```

---

## Self-Review

**Spec coverage:**

| Spec element | Task |
|---|---|
| RSS collector (Autosport/Race/Motorsport/RACER) | Task 7 + config in Task 1 |
| GDELT discovery + spike signal | Task 8 |
| Reddit engagement layer | Task 9 |
| Skip X/Twitter | (nothing built — correct) |
| Stage 1 collect (24h UTC window) | Task 12 `_collect` + `run` window |
| Stage 2 normalize (URL canon, series) | Task 2 |
| Stage 3 cluster (URL + fuzzy title, breadth signal) | Task 3 |
| Stage 4 score (rank-normalize, weighted sum, driver-noise mitigation) | Task 4 + `is_relevant` in Task 8 |
| Stage 5 gate (threshold, suppress window, escalation, no-email-on-quiet-day) | Task 6 + `run` in Task 12 |
| Stage 6 summarize (Haiku 4.5, titles + Reddit, no scraping) | Task 10 |
| Stage 7 send (HTML email, SES, record state) | Task 11 + `run` in Task 12 |
| Calibration mode | Task 6 gate + Task 12 logging + config default |
| SQLite state store | Task 5 |
| Blurb-per-story format, ranked, ungrouped | Task 11 render |
| Keyword scope: series + teams + drivers | Task 1 config + Task 8 |
| Pi deployment, systemd timer | Task 13 |
| Config/secrets (12-factor, .env) | Task 1 |
| --dry-run for stages 1–5 | Task 12 |
| Module layout from spec | Tasks 2–12 |

All spec sections map to a task. No gaps.

**Placeholder scan:** No TBD/TODO/"add error handling"/"write tests for the above" — every code and test step contains real content. Error handling is concrete (per-source try/except with logging; summarize title-fallback).

**Type consistency:** `RawItem` / `Story` / `ScoredStory` / `Blurb` field names are used identically across Tasks 2–12. `Config` fields referenced in later tasks (`weights`, `keywords`, `calibration`, `suppress_days`, `escalation_factor`, `threshold`, `max_stories`, `db_path`, `rss_feeds`, `subreddits`, `ses_*`, secrets) all match Task 1's definition. `filter_stories`, `score_stories`, `cluster_items`, `rank`, `summarize`, `render_html`/`send_email` signatures match between definition and call sites.

One deliberate note carried into the plan: `fetch_gdelt` (Task 8) is thin glue over tested pure functions, flagged for the implementer to verify `gdeltdoc` column names against the installed version — the DataFrame shape is the one thing that can't be pinned without the live library.
