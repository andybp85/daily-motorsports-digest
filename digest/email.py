import html as html_lib

from digest.models import Blurb

_SAFE_SCHEMES = ("http://", "https://")


def render_subject(date) -> str:
    return f"🏎️ Morning Buzz — {date:%a %b %-d, %Y}"


def _story_link(blurb: Blurb) -> str:
    url = blurb.scored.story.canonical_url
    return url if url.startswith(_SAFE_SCHEMES) else "#"


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
