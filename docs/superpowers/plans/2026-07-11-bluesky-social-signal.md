# Bluesky Social-Engagement Signal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the digest a real per-story ranking signal by scoring how much each story's article is shared/engaged with on Bluesky.

**Architecture:** A post-cluster *enrichment* stage (not a collector): after `cluster_items`, for each `Story` find Bluesky posts linking its `canonical_url`, sum `like+repost+reply`, and append one synthetic engagement `RawItem` so the existing (renamed `reddit → social`) scoring signal picks it up. The stage is injected into `pipeline.score_pool` via an optional `enrich` callable and degrades cleanly when disabled or failing.

**Tech Stack:** Python 3.11+, stdlib `urllib` for Bluesky XRPC (no new dependency), `pytest`, `ruff`, `uv`.

**Spec:** `docs/superpowers/specs/2026-07-11-bluesky-social-signal-design.md`

## Global Constraints

- Python `>=3.11`; new files use 4-space indent; max line length 140.
- Annotate every function signature (params + return, incl. `-> None`).
- No new third-party dependency — Bluesky I/O uses stdlib `urllib`.
- Secrets (`BSKY_HANDLE`, `BSKY_APP_PASSWORD`) come from env only; never commit them, never write them to a bean.
- Follow the existing collector degradation pattern: any Bluesky failure prints `[bluesky] …` and leaves the digest running on its other signals. One story's failure must not kill the run.
- Run tests with `PYTHONPATH=. .venv/bin/python -m pytest` from the repo root.
- Bean `daily-motorsports-digest-qzme` tracks this work; check off its todos and commit the bean file with the code.

## File Structure

- Create: `digest/collect/bluesky.py` — pure matching helpers, `BlueskyClient` (thin I/O), `enrich()`.
- Create: `tests/test_bluesky.py` — unit tests for helpers + `enrich` with a fake client.
- Modify: `digest/score.py` — rename the `reddit` signal to `social`.
- Modify: `digest/config.py` — load `bluesky_enabled`, `bsky_handle`, `bsky_app_password`.
- Modify: `digest/pipeline.py` — add `enrich` seam to `score_pool`.
- Modify: `digest/main.py` — build a `BlueskyClient` and pass the enrich callable.
- Modify: `config.toml`, `config.example.toml` — `[weights] social`, `bluesky_enabled`.
- Modify: `.env.example` — `BSKY_HANDLE`, `BSKY_APP_PASSWORD`.
- Modify: `tests/test_score.py`, `tests/test_pipeline.py` — `reddit` weight key → `social`.

---

### Task 1: Feasibility gate (spike — decides model A vs. fallback)

Not TDD; an exploratory decision that gates the *matcher* only. The rest of the plan (Tasks 2–7) is identical either way.

**Files:** none committed (probe lives in a scratch dir).

- [ ] **Step 1: Get a fresh Bluesky app password**

Ask the user to create one (bsky.app → Settings → Privacy & Security → App Passwords) and export it for this session only:

```bash
export BSKY_HANDLE='<their-handle-or-email>'
export BSKY_APP_PASSWORD='<fresh-app-password>'
```

- [ ] **Step 2: Run the match probe against real stories**

Reuse `scratchpad/bsky_match_probe.py` from the design session (or re-create it): for today's top ~6 RSS stories it reports, per story, how many Bluesky posts link the article (direct URL search + title-terms + embed match) and their total engagement.

Run: `BSKY_APP_PASSWORD=$BSKY_APP_PASSWORD PYTHONPATH=. .venv/bin/python scratchpad/bsky_match_probe.py`

- [ ] **Step 3: Decide and record**

- **GO** (several F1 stories show ≥1 linking post with real engagement) → implement Tasks 2–7 as written (model A).
- **THIN** (URL-matching finds almost nothing) → still implement Tasks 2–7, but replace the matcher in Task 4/5 with the **Contingency** section at the end.

Write the decision + the raw numbers into bean `qzme` (numbers only — never the password).

---

### Task 2: Rename the `reddit` signal to `social`

Pure rename. No behavior change (the signal is still unpopulated until Bluesky lands), so the digest is fully working after this task. This unblocks feeding Bluesky engagement into it.

**Files:**
- Modify: `digest/score.py:25-26` (`_reddit_signal`), `digest/score.py:45` (`weights["reddit"]`)
- Modify: `config.toml` (`[weights]`), `config.example.toml` (`[weights]`)
- Test: `tests/test_score.py:4`, `tests/test_pipeline.py:17`

**Interfaces:**
- Produces: `score_stories(stories, series_spike, weights)` now reads `weights["social"]` instead of `weights["reddit"]`; helper `_social_signal(story) -> float` (sums each item's `reddit_score + reddit_comments`, unchanged body).

- [ ] **Step 1: Update the score tests to the new key/name**

In `tests/test_score.py`, change the weights fixture:

```python
WEIGHTS = {"social": 0.5, "breadth": 0.35, "spike": 0.15}
```

In `tests/test_pipeline.py`, change the inline weights (line ~17):

```python
        weights={"social": 0.5, "breadth": 0.35, "spike": 0.15},
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_score.py tests/test_pipeline.py -q`
Expected: FAIL — `score_stories` still reads `weights["reddit"]`, raising `KeyError: 'reddit'`.

- [ ] **Step 3: Rename in `score.py`**

Rename the helper and the weight key:

```python
def _social_signal(story: Story) -> float:
    return float(sum(i.reddit_score + i.reddit_comments for i in story.items))
```

In `score_stories`, update the call and the weight lookup:

```python
    social_raw = [_social_signal(s) for s in stories]
    ...
    social_rank = rank_normalize(social_raw)
    ...
        buzz = (weights["social"] * social_rank[i]
                + weights["breadth"] * breadth_rank[i]
                + weights["spike"] * spike_rank[i])
        scored.append(ScoredStory(
            story=story, reddit_raw=social_raw[i], breadth_raw=breadth_raw[i],
            spike_raw=spike_raw[i], buzz=buzz,
        ))
```

Note: `ScoredStory.reddit_raw` field name is intentionally kept (documented in the spec) — only the signal/weight is renamed.

- [ ] **Step 4: Update `config.toml` and `config.example.toml`**

Under `[weights]`, rename `reddit` to `social` (keep the value):

```toml
[weights]
social = 0.5
breadth = 0.35
spike = 0.15
```

- [ ] **Step 5: Run the full suite to verify green**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q`
Expected: PASS (all tests).

- [ ] **Step 6: Commit**

```bash
git add digest/score.py config.toml config.example.toml tests/test_score.py tests/test_pipeline.py
git commit -m "refactor: rename reddit ranking signal to social"
```

---

### Task 3: Load Bluesky config (toggle + creds)

**Files:**
- Modify: `digest/config.py` (dataclass fields + `load_config`)
- Modify: `config.toml`, `config.example.toml` (add `bluesky_enabled`)
- Modify: `.env.example` (add `BSKY_*`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `Config` gains `bluesky_enabled: bool = False`, `bsky_handle: str = ""`, `bsky_app_password: str = ""`. `load_config` reads `bluesky_enabled` from TOML and `BSKY_HANDLE` / `BSKY_APP_PASSWORD` from env.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_config.py`:

```python
def test_load_config_reads_bluesky(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text('bluesky_enabled = true\n')
    monkeypatch.setenv("BSKY_HANDLE", "andy.example.com")
    monkeypatch.setenv("BSKY_APP_PASSWORD", "abcd-efgh-ijkl-mnop")

    cfg = load_config(str(cfg_file))

    assert cfg.bluesky_enabled is True
    assert cfg.bsky_handle == "andy.example.com"
    assert cfg.bsky_app_password == "abcd-efgh-ijkl-mnop"
```

Ensure `from digest.config import load_config` is imported at the top of the test file (it already is if other config tests exist; add it if not).

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_config.py::test_load_config_reads_bluesky -q`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'bluesky_enabled'`.

- [ ] **Step 3: Add the fields and loader lines**

In `digest/config.py`, add to the `Config` dataclass (with the other secret fields):

```python
    bluesky_enabled: bool = False
    bsky_handle: str = ""
    bsky_app_password: str = ""
```

In `load_config`, add to the `Config(...)` construction:

```python
        bluesky_enabled=bool(data.get("bluesky_enabled", False)),
        bsky_handle=os.environ.get("BSKY_HANDLE", ""),
        bsky_app_password=os.environ.get("BSKY_APP_PASSWORD", ""),
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_config.py -q`
Expected: PASS.

- [ ] **Step 5: Document the toggle and creds**

In `config.toml` and `config.example.toml`, add near `reddit_enabled`:

```toml
# Bluesky enrichment: scores each story by how much its article is shared on
# Bluesky. Needs BSKY_HANDLE + BSKY_APP_PASSWORD in .env. Disabled by default.
bluesky_enabled = false
```

In `.env.example`, add:

```bash
# Bluesky — app password (bsky.app → Settings → App Passwords). Read-only use.
BSKY_HANDLE=
BSKY_APP_PASSWORD=
```

- [ ] **Step 6: Commit**

```bash
git add digest/config.py config.toml config.example.toml .env.example tests/test_config.py
git commit -m "feat: load Bluesky config (toggle + app-password creds)"
```

---

### Task 4: Bluesky pure matching helpers

**Files:**
- Create: `digest/collect/bluesky.py`
- Test: `tests/test_bluesky.py`

**Interfaces:**
- Produces:
  - `normalize_url(url: str) -> str`
  - `external_uri(post: dict) -> str`
  - `post_links_story(post: dict, story_url: str) -> bool`
  - `match_posts(story: Story, posts: list[dict]) -> list[dict]`
  - `engagement(posts: list[dict]) -> int`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_bluesky.py`:

```python
from digest.collect.bluesky import (
    engagement,
    external_uri,
    match_posts,
    normalize_url,
    post_links_story,
)
from digest.models import RawItem, Story


def _story(url: str) -> Story:
    return Story(key="k", canonical_url=url, title="Verstappen wins at Spa",
                 series="f1", items=[RawItem(source="rss", url=url, title="t", domain="d")])


def _post(uri: str = "", text: str = "", likes: int = 0, reposts: int = 0, replies: int = 0) -> dict:
    embed = {"$type": "app.bsky.embed.external", "external": {"uri": uri}} if uri else {}
    return {"record": {"text": text, "embed": embed},
            "likeCount": likes, "repostCount": reposts, "replyCount": replies}


def test_normalize_url_strips_scheme_www_query_slash():
    assert normalize_url("https://www.Autosport.com/f1/news/x/?utm=1#top") == "autosport.com/f1/news/x"
    assert normalize_url("http://the-race.com/feed/") == "the-race.com/feed"


def test_external_uri_reads_embed_or_empty():
    assert external_uri(_post(uri="https://a.com/1")) == "https://a.com/1"
    assert external_uri(_post(text="no embed")) == ""


def test_post_links_story_matches_embed_or_raw_link():
    story = _story("https://autosport.com/f1/news/x")
    assert post_links_story(_post(uri="https://www.autosport.com/f1/news/x/"), story.canonical_url)
    assert post_links_story(_post(text="great read https://autosport.com/f1/news/x"), story.canonical_url)
    assert not post_links_story(_post(uri="https://other.com/y", text="off topic"), story.canonical_url)


def test_match_posts_filters_to_linking_posts():
    story = _story("https://autosport.com/f1/news/x")
    posts = [_post(uri="https://autosport.com/f1/news/x", likes=5),
             _post(uri="https://other.com/y", likes=99)]
    assert [p["likeCount"] for p in match_posts(story, posts)] == [5]


def test_engagement_sums_like_repost_reply():
    assert engagement([_post(likes=3, reposts=2, replies=1), _post(likes=10)]) == 16
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_bluesky.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'digest.collect.bluesky'`.

- [ ] **Step 3: Implement the helpers**

Create `digest/collect/bluesky.py`:

```python
import re

from digest.models import Story


def normalize_url(url: str) -> str:
    """Comparison form: lowercase, no scheme/www, no query/fragment, no trailing slash."""
    stripped = re.sub(r"^https?://(www\.)?", "", url.strip().lower())
    stripped = stripped.split("?")[0].split("#")[0]
    return stripped.rstrip("/")


def external_uri(post: dict) -> str:
    """The article URI from a post's external embed, or '' when there is none."""
    embed = post.get("record", {}).get("embed", {}) or {}
    if str(embed.get("$type", "")).startswith("app.bsky.embed.external"):
        return embed.get("external", {}).get("uri", "")
    return ""


def post_links_story(post: dict, story_url: str) -> bool:
    """True if the post links the story's article via embed card or a raw link in text."""
    target = normalize_url(story_url)
    if not target:
        return False
    if normalize_url(external_uri(post)) == target:
        return True
    text = (post.get("record", {}).get("text", "") or "").lower()
    return target in text


def match_posts(story: Story, posts: list[dict]) -> list[dict]:
    """Posts (from a search) that actually link the story's article."""
    return [p for p in posts if post_links_story(p, story.canonical_url)]


def engagement(posts: list[dict]) -> int:
    """Total like + repost + reply across posts."""
    return sum(p.get("likeCount", 0) + p.get("repostCount", 0) + p.get("replyCount", 0)
               for p in posts)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_bluesky.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add digest/collect/bluesky.py tests/test_bluesky.py
git commit -m "feat: Bluesky post-to-story matching helpers"
```

---

### Task 5: `BlueskyClient` + `enrich()`

**Files:**
- Modify: `digest/collect/bluesky.py` (add `BlueskyClient`, `_title_terms`, `_story_posts`, `enrich`)
- Test: `tests/test_bluesky.py` (add `enrich` tests with a fake client)

**Interfaces:**
- Consumes: `match_posts`, `engagement` (Task 4); `RawItem`, `Story` from `digest.models`.
- Produces:
  - `BlueskyClient(handle: str, app_password: str, timeout: float = 15.0)` with `search_posts(query: str, *, limit: int = 100, sort: str = "top") -> list[dict]`.
  - `enrich(stories: list[Story], client: object | None) -> list[Story]` — appends a synthetic `RawItem(source="bluesky", reddit_score=engagement(...))` to each story that has linking posts; returns stories unchanged when `client is None`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_bluesky.py`:

```python
from digest.collect.bluesky import enrich


class _FakeClient:
    """Returns canned search results keyed by whether the query is the story URL."""

    def __init__(self, by_query: dict):
        self.by_query = by_query
        self.calls = []

    def search_posts(self, query, *, limit=100, sort="top"):
        self.calls.append(query)
        return self.by_query.get(query, [])


def test_enrich_appends_engagement_item_for_linked_story():
    url = "https://autosport.com/f1/news/x"
    story = _story(url)
    client = _FakeClient({url: [_post(uri=url, likes=4, reposts=1, replies=2)]})

    (out,) = enrich([story], client)

    bsky_items = [i for i in out.items if i.source == "bluesky"]
    assert len(bsky_items) == 1
    assert bsky_items[0].reddit_score == 7          # 4 + 1 + 2


def test_enrich_falls_back_to_title_search_when_url_search_empty():
    url = "https://autosport.com/f1/news/x"
    story = _story(url)                              # title "Verstappen wins at Spa"
    client = _FakeClient({"Verstappen wins Spa": [_post(uri=url, likes=5)]})

    (out,) = enrich([story], client)

    assert any(i.source == "bluesky" and i.reddit_score == 5 for i in out.items)


def test_enrich_leaves_unlinked_story_untouched():
    story = _story("https://autosport.com/f1/news/x")
    client = _FakeClient({})                         # no posts for anything

    (out,) = enrich([story], client)

    assert not any(i.source == "bluesky" for i in out.items)


def test_enrich_no_client_is_noop():
    story = _story("https://autosport.com/f1/news/x")
    (out,) = enrich([story], None)
    assert not any(i.source == "bluesky" for i in out.items)


def test_enrich_one_story_failure_does_not_kill_run():
    class _Boom:
        def search_posts(self, *a, **k):
            raise RuntimeError("network down")
    story = _story("https://autosport.com/f1/news/x")
    (out,) = enrich([story], _Boom())                # must not raise
    assert not any(i.source == "bluesky" for i in out.items)
```

Note: `test_enrich_falls_back...` assumes `_title_terms("Verstappen wins at Spa")` == `"Verstappen wins Spa"` (words > 3 chars: "Verstappen", "wins", "Spa"; "at" dropped). Keep `_title_terms` consistent with this.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_bluesky.py -k enrich -q`
Expected: FAIL — `ImportError: cannot import name 'enrich'`.

- [ ] **Step 3: Implement the client and enrich**

Append to `digest/collect/bluesky.py` (add `import json`, `import urllib.parse`, `import urllib.request`, and `from digest.models import RawItem` at the top):

```python
_BSKY_API = "https://bsky.social/xrpc"


class BlueskyClient:
    """Thin authenticated wrapper over the Bluesky search endpoint (stdlib only).

    Each HTTP call is bounded by `timeout` so a stalled endpoint can't hang the
    digest — the same failure mode fixed for GDELT.
    """

    def __init__(self, handle: str, app_password: str, timeout: float = 15.0) -> None:
        self._timeout = timeout
        self._token = self._create_session(handle, app_password)

    def _create_session(self, identifier: str, password: str) -> str:
        body = json.dumps({"identifier": identifier, "password": password}).encode()
        req = urllib.request.Request(
            f"{_BSKY_API}/com.atproto.server.createSession",
            data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.load(resp)["accessJwt"]

    def search_posts(self, query: str, *, limit: int = 100, sort: str = "top") -> list[dict]:
        params = urllib.parse.urlencode({"q": query, "limit": limit, "sort": sort})
        req = urllib.request.Request(
            f"{_BSKY_API}/app.bsky.feed.searchPosts?{params}",
            headers={"Authorization": f"Bearer {self._token}"})
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.load(resp).get("posts", [])


def _title_terms(title: str, n: int = 6) -> str:
    """A few significant words from the headline for a text search."""
    words = [w for w in re.findall(r"[A-Za-z0-9']+", title) if len(w) > 3]
    return " ".join(words[:n])


def _story_posts(story: Story, client: object) -> list[dict]:
    """Posts linking the story: direct URL search first, title-terms fallback."""
    hits = match_posts(story, client.search_posts(story.canonical_url, sort="latest"))
    if hits:
        return hits
    return match_posts(story, client.search_posts(_title_terms(story.title)))


def enrich(stories: list[Story], client: object | None) -> list[Story]:
    """Attach a synthetic Bluesky engagement item to each story with linking posts.

    No-op when `client` is None. One story's search failure is logged and skipped
    so it cannot kill the run.
    """
    if client is None:
        return stories
    for story in stories:
        try:
            posts = _story_posts(story, client)
        except Exception as exc:                    # noqa: BLE001 — one story must not kill the run
            print(f"[bluesky] search failed for {story.canonical_url}: {exc}")
            continue
        if not posts:
            continue
        story.items.append(RawItem(
            source="bluesky", url=story.canonical_url, title=story.title,
            reddit_score=engagement(posts), series=story.series,
        ))
    return stories
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_bluesky.py -q`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git add digest/collect/bluesky.py tests/test_bluesky.py
git commit -m "feat: BlueskyClient + per-story engagement enrichment"
```

---

### Task 6: Wire the enrich seam into `pipeline.score_pool`

**Files:**
- Modify: `digest/pipeline.py` (`score_pool` signature + body)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: nothing new (enrich is passed in by the caller).
- Produces: `score_pool(raw_items, series_spike, cfg, enrich=None)` — when `enrich` is not None it is applied to the clustered stories before scoring; `enrich: list[Story] -> list[Story]`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_pipeline.py`:

```python
def test_score_pool_applies_enrich_between_cluster_and_score():
    calls = {"n": 0}
    def fake_enrich(stories):
        calls["n"] = len(stories)
        return stories
    # reuse whatever RawItem fixtures the other pipeline tests use
    items = _sample_items()                          # existing helper in this file
    cfg = _sample_cfg()                              # existing helper in this file

    score_pool(items, {"f1": 1.0}, cfg, enrich=fake_enrich)

    assert calls["n"] > 0                            # enrich saw the clustered stories
```

If `tests/test_pipeline.py` has no `_sample_items()/_sample_cfg()` helpers, inline the same construction the file's existing `score_pool`/`rank` test already uses.

- [ ] **Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pipeline.py::test_score_pool_applies_enrich_between_cluster_and_score -q`
Expected: FAIL — `TypeError: score_pool() got an unexpected keyword argument 'enrich'`.

- [ ] **Step 3: Add the enrich seam**

In `digest/pipeline.py`, update `score_pool`:

```python
def score_pool(raw_items: list[RawItem], series_spike: dict[str, float], cfg: Config,
               enrich=None) -> list[ScoredStory]:
    """Pure normalize → cluster → [enrich] → score. Returns the pre-gate pool, sorted desc."""
    normalized = normalize_items(raw_items, cfg.keywords)
    stories = cluster_items(normalized)
    if enrich is not None:
        stories = enrich(stories)
    return score_stories(stories, series_spike, cfg.weights)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_pipeline.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add digest/pipeline.py tests/test_pipeline.py
git commit -m "feat: add optional enrich seam to score_pool"
```

---

### Task 7: Wire Bluesky into `main.run` + smoke-verify

**Files:**
- Modify: `digest/main.py` (import, client factory, pass enrich to `score_pool`)

**Interfaces:**
- Consumes: `score_pool(..., enrich=...)` (Task 6); `bluesky.BlueskyClient`, `bluesky.enrich` (Task 5); `cfg.bluesky_enabled/bsky_handle/bsky_app_password` (Task 3).
- Produces: no new public interface — behavior wired end to end.

- [ ] **Step 1: Add the client factory**

In `digest/main.py`, add the import and a helper:

```python
from digest.collect import bluesky


def _bluesky_client(cfg):
    """A logged-in BlueskyClient, or None when disabled/unconfigured/auth fails."""
    if not cfg.bluesky_enabled:
        print("[bluesky] disabled via config (bluesky_enabled = false) — skipping")
        return None
    if not (cfg.bsky_handle and cfg.bsky_app_password):
        print("[bluesky] no credentials configured — skipping")
        return None
    try:
        return bluesky.BlueskyClient(cfg.bsky_handle, cfg.bsky_app_password)
    except Exception as exc:                        # noqa: BLE001 — degrade, never crash the run
        print(f"[bluesky] auth failed: {exc} — skipping")
        return None
```

- [ ] **Step 2: Pass the enrich callable into `score_pool`**

In `run`, replace the `scored = score_pool(raw, spikes, cfg)` line with:

```python
        client_bsky = _bluesky_client(cfg)
        enrich = (lambda stories: bluesky.enrich(stories, client_bsky)) if client_bsky else None
        scored = score_pool(raw, spikes, cfg, enrich=enrich)          # full pre-gate pool, sorted desc
```

- [ ] **Step 3: Verify the suite still passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q`
Expected: PASS (all tests).

- [ ] **Step 4: Smoke-test disabled path (no creds needed)**

With `bluesky_enabled = false` (default), run a dry-run:

Run: `PYTHONPATH=. .venv/bin/python -m digest.main --config config.toml --dry-run`
Expected: prints `[bluesky] disabled via config … — skipping`, then the normal `[dry-run] N stories would be sent` output. No crash.

- [ ] **Step 5: Smoke-test enabled path (needs the fresh app password from Task 1)**

Temporarily set `bluesky_enabled = true` in `config.toml`, export `BSKY_HANDLE`/`BSKY_APP_PASSWORD`, and run:

Run: `PYTHONPATH=. .venv/bin/python -m digest.main --config config.toml --dry-run`
Expected: no `[bluesky]` error lines; the dry-run completes. If any F1 story matched posts, its buzz should now differ from the flat baseline (scores no longer all identical). Revert `bluesky_enabled` to `false` before committing unless you intend to enable it in the deploy.

- [ ] **Step 6: Commit**

```bash
git add digest/main.py config.toml
git commit -m "feat: wire Bluesky enrichment into the digest run"
```

- [ ] **Step 7: Close out the bean**

Check off `qzme`'s todos and add a `## Summary of Changes` section; mark it completed if no todos remain.

```bash
beans update daily-motorsports-digest-qzme -s completed --body-append "## Summary of Changes

Added post-cluster Bluesky enrichment (model A): per-story article-URL match → sum like+repost+reply into the renamed social signal. Feasibility gate result: <GO/THIN + numbers>. Config-gated (bluesky_enabled), degrades cleanly, stdlib-only I/O."
git add .beans/daily-motorsports-digest-qzme--add-bluesky-as-a-data-source.md
git commit -m "chore: close bean qzme (Bluesky social signal)"
```

---

## Contingency: guarded per-entity matcher (only if Task 1 gate = THIN)

If URL-matching is too sparse, replace `_story_posts` (Task 5) with a keyword search filtered through the existing relevance gate, so surname noise (Bertrand Russell, Chuck Norris, the *Grand Prix* film) is discarded before counting engagement.

**Files:** Modify `digest/collect/bluesky.py`; add a test to `tests/test_bluesky.py`.

- [ ] **Step 1: Write the failing test**

```python
from digest.collect.bluesky import _relevant_posts

def test_relevant_posts_drops_off_topic_by_is_relevant():
    keywords = {"series_f1": ["F1", "Grand Prix"], "anchors": ["F1", "racing"],
                "teams": [], "drivers": ["Verstappen"]}
    posts = [_post(text="Verstappen wins the F1 Grand Prix", likes=3),
             _post(text="Bertrand Russell on the ethics of war", likes=500)]
    kept = _relevant_posts(posts, keywords)
    assert [p["likeCount"] for p in kept] == [3]
```

- [ ] **Step 2: Run to verify it fails**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_bluesky.py::test_relevant_posts_drops_off_topic_by_is_relevant -q`
Expected: FAIL — `ImportError: cannot import name '_relevant_posts'`.

- [ ] **Step 3: Implement the guarded matcher**

Add to `digest/collect/bluesky.py` (import `from digest.normalize import is_relevant`):

```python
def _relevant_posts(posts: list[dict], keywords: dict) -> list[dict]:
    """Keep only posts whose text passes the motorsport relevance gate."""
    return [p for p in posts if is_relevant(p.get("record", {}).get("text", ""), keywords)]
```

Then change `_story_posts` to search by the story's series terms and filter:

```python
def _story_posts(story: Story, client: object, keywords: dict) -> list[dict]:
    """URL-linking posts first; fall back to relevance-gated series-keyword search."""
    hits = match_posts(story, client.search_posts(story.canonical_url, sort="latest"))
    if hits:
        return hits
    series_terms = keywords.get(f"series_{story.series}", [])
    query = " ".join(series_terms[:3]) or _title_terms(story.title)
    return _relevant_posts(client.search_posts(query), keywords)
```

`enrich` then needs `keywords` threaded through: `enrich(stories, client, keywords=None)`, and Task 7's lambda becomes `lambda s: bluesky.enrich(s, client_bsky, cfg.keywords)`. Update the Task 5 `enrich` tests to pass `keywords={}` (URL path unaffected).

- [ ] **Step 4: Run to verify pass**, then **Step 5: Commit** (`feat: guarded per-entity Bluesky fallback matcher`).

---

## Self-Review

- **Spec coverage:** enrichment-not-collector (Task 5–6), two-pass short-circuit match (Task 5 `_story_posts`), URL normalization (Task 4), repurpose reddit→social via synthetic item (Task 2 + Task 5), config/toggle/creds + `.env` (Task 3), degradation + per-call timeout (Task 5 `BlueskyClient`, `enrich`), pipeline seam (Task 6), main wiring (Task 7), feasibility gate (Task 1), fallback (Contingency), tests with injected fake client (Tasks 4–6). All spec sections map to a task.
- **Placeholders:** none — the only intentional fill-in is `<GO/THIN + numbers>` in the bean summary (a runtime result), which is correct.
- **Type consistency:** `enrich(stories, client)` signature consistent across Tasks 5–7 (Contingency extends it to `(stories, client, keywords)` and updates callers/tests in the same task). `search_posts(query, *, limit, sort)` consistent between `BlueskyClient` and `_FakeClient`. `score_pool(..., enrich=None)` consistent between Task 6 and Task 7. `_social_signal` / `weights["social"]` consistent between Task 2 and the score fixtures.
