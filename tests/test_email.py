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


def test_render_html_names_the_linked_outlet():
    blurbs = [_blurb("Verstappen wins", "Max takes it.", 10, 2, ["www.autosport.com"])]
    html = render_html(blurbs, date(2026, 7, 3))
    assert ">autosport.com</a>" in html  # named, and the www. is stripped
    assert ">source</a>" not in html  # the old placeholder word is gone


def test_render_html_falls_back_to_source_when_link_is_unusable():
    """An unsafe URL is already downgraded to '#', which has no host to name.

    The label must not come out blank — a bare '·' with nothing to click reads
    as a rendering bug, so it degrades to the old placeholder word.
    """
    blurbs = [_blurb("Title", "Blurb text", 10, 2, ["a.com"])]
    blurbs[0].scored.story.canonical_url = "javascript:alert(1)"
    html = render_html(blurbs, date(2026, 7, 3))
    assert '<a href="#">source</a>' in html


def test_render_html_escapes_the_outlet_name():
    blurbs = [_blurb("Title", "Blurb text", 10, 2, ["a.com"])]
    blurbs[0].scored.story.canonical_url = 'https://evil"<script>.com/x'
    html = render_html(blurbs, date(2026, 7, 3))
    assert "<script>" not in html


def test_render_html_labels_engagement_source_neutrally():
    """The engagement number is whatever social collector ran (Bluesky today),
    not Reddit upvotes — the meta line must not call it 'upvotes+comments'.
    """
    blurbs = [_blurb("Verstappen wins", "Max takes it.", 10, 2, ["a.com", "b.com"])]
    html = render_html(blurbs, date(2026, 7, 3))
    assert "upvotes" not in html
    assert "12 reactions" in html  # score + comments, source-neutral


def test_render_html_pluralizes_the_reaction_count():
    one = _blurb("Solo", "Barely shared.", 1, 0, ["a.com"])
    html = render_html([one], date(2026, 7, 3))
    assert "1 reaction" in html and "1 reactions" not in html


def test_render_html_pluralizes_the_outlet_count():
    one = _blurb("Solo", "Only one outlet ran it.", 10, 2, ["a.com"])
    html = render_html([one], date(2026, 7, 3))
    assert "1 outlet" in html and "1 outlets" not in html

    two = _blurb("Shared", "Two outlets ran it.", 10, 2, ["a.com", "b.com"])
    html = render_html([two], date(2026, 7, 3))
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


def test_render_html_drops_unsafe_link_scheme():
    blurbs = [_blurb("Title", "Blurb text", 10, 2, ["a.com"])]
    blurbs[0].scored.story.canonical_url = "javascript:alert(1)"
    html = render_html(blurbs, date(2026, 7, 3))
    assert "javascript:alert(1)" not in html
    assert 'href="#"' in html


def test_render_html_escapes_feed_content():
    blurbs = [_blurb('<script>alert(1)</script>', 'Tom & "Jerry" <b>win</b>', 100, 5, ["a.com"])]
    html = render_html(blurbs, date(2026, 7, 3))

    assert "<script>alert(1)</script>" not in html      # raw markup must not survive
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html   # escaped form present
    assert "Tom &amp; " in html                          # ampersand escaped
    assert "&quot;Jerry&quot;" in html                   # quotes escaped (html.escape quote=True)
