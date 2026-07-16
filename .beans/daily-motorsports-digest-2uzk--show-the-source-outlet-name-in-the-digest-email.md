---
# daily-motorsports-digest-2uzk
title: Show the source outlet name in the digest email
status: completed
type: feature
created_at: 2026-07-16T20:09:18Z
updated_at: 2026-07-16T20:09:18Z
parent: daily-motorsports-digest-z6pt
---

The email meta line linked each story under the literal word "source". It now names the outlet: `autosport.com · 5100 upvotes+comments · 2 outlets`.

## Decisions

- **Name the linked outlet only**, not every outlet in the cluster. The adjacent "N outlets" count already signals there are others, and listing them all is unbounded for a widely-covered story.
- **Cleaned domain** (`autosport.com`), not a prettified display name (`Autosport`). A display-name table needs upkeep and GDELT surfaces a long tail of outlets it would never cover — the fallback would be the domain anyway.
- **Derive the name from `canonical_url`**, not from the head `RawItem.domain`. The two agree today only because `cluster_items()` takes `canonical_url` from the same item; reading the URL means the label can never disagree with the link it sits on.

## Also fixed

Pluralization of the adjacent count — it read "1 outlets".

## Summary of Changes

- `digest/email.py`: new `_outlet_name()` helper; meta line names the outlet and pluralizes the count.
- `tests/test_email.py`: four tests — name rendered + www. stripped, unsafe-URL fallback to "source", outlet name escaped, count pluralized.

Unsafe URLs were already downgraded to `#` by `_story_link()`; `_outlet_name()` falls back to the word "source" there so the label is never blank.

## Verification

Rendered a sample with realistic stories including the hostile-URL case: `www.` stripped, links intact, "1 outlet"/"2 outlets" correct, `javascript:` URL renders `<a href="#">source</a>`. 108 tests pass.
