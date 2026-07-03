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
