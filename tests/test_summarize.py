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
