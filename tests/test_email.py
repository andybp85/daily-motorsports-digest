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
