import json
import re

from digest.models import Blurb, ScoredStory

_SYSTEM = (
    "You write concise motorsport news blurbs. For each story you are given a "
    "headline, its sources, and a social engagement score (how widely the story "
    "is being shared and discussed). Write a punchy 2-3 sentence blurb per story "
    "capturing what happened and why it's buzzing. The engagement score is a "
    "ranking signal, not a fact about the story — do not name a platform or "
    "comment on how high or low it is. Do not invent facts beyond the headline "
    "and stats. Respond with ONLY a JSON array of objects: "
    "[{\"index\": <int>, \"blurb\": <string>}]."
)


def build_prompt(scored: list[ScoredStory]) -> str:
    lines = []
    for i, s in enumerate(scored):
        story = s.story
        domains = ", ".join(sorted(story.domains)) or "n/a"
        lines.append(
            f"[{i}] {story.title}\n"
            f"    sources: {domains}\n"
            f"    engagement: {int(s.reddit_raw)} across {int(s.breadth_raw)} outlets"
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
