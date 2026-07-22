from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SeriesDef:
    """One followed motorsport series and the title terms that identify it."""

    id: str  # lowercase slug: "f1", "wec", ...
    label: str  # display name: "Formula 1", "WEC"
    terms: tuple[str, ...]  # distinctive identifiers; whole-token (word-boundary) matched


@dataclass(frozen=True)
class Tier:
    """A priority band of series with a guaranteed floor of digest slots.

    Tiers are applied in order: each reserves up to `floor` of its highest-buzz
    stories before the remaining slots fill by buzz across everything. A series
    named in no tier has floor 0 — it competes only in the buzz fill.
    """

    series: frozenset[str]  # series ids that belong to this tier
    floor: int  # minimum slots reserved (a minimum, not a cap)


@dataclass
class RawItem:
    """A single item from one source before clustering."""

    source: str  # "rss" | "gdelt" | "reddit"
    url: str
    title: str
    domain: str = ""
    published_at: datetime | None = None
    reddit_score: int = 0
    reddit_comments: int = 0
    series: str = ""  # a followed series id, or "" (RawItem, pre-classification)
    extra: dict = field(default_factory=dict)


@dataclass
class Story:
    """A cluster of RawItems referring to the same event across sources."""

    key: str  # canonical url + title hash
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
