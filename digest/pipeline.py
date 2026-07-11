from collections.abc import Callable

from digest.cluster import cluster_items
from digest.config import Config
from digest.gate import filter_stories
from digest.models import RawItem, ScoredStory, Story
from digest.normalize import normalize_items
from digest.score import score_stories


def score_pool(raw_items: list[RawItem], series_spike: dict[str, float], cfg: Config,
               enrich: Callable[[list[Story]], list[Story]] | None = None) -> list[ScoredStory]:
    """Pure normalize → cluster → [enrich] → score. Returns the day's full pre-gate pool, sorted by buzz desc."""
    normalized = normalize_items(raw_items, cfg.keywords)
    stories = cluster_items(normalized)
    if enrich is not None:
        stories = enrich(stories)
    return score_stories(stories, series_spike, cfg.weights)


def rank(raw_items: list[RawItem], series_spike: dict[str, float],
         state, cfg: Config) -> list[ScoredStory]:
    """score_pool → gate. Returns surviving scored stories."""
    scored = score_pool(raw_items, series_spike, cfg)
    return filter_stories(
        scored, state,
        threshold=cfg.threshold, calibration=cfg.calibration,
        suppress_days=cfg.suppress_days, escalation_factor=cfg.escalation_factor,
    )
