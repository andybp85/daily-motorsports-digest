---
# daily-motorsports-digest-edx5
title: Digest mislabels Bluesky engagement as Reddit
status: completed
type: bug
created_at: 2026-07-18T16:34:53Z
updated_at: 2026-07-18T16:34:53Z
parent: daily-motorsports-digest-z6pt
---

Spotted in the Sat 2026-07-18 email: a summary blurb read "...limited Reddit engagement despite the championship rivalry implications" — but Reddit is disabled (reddit_enabled=false). The engagement signal is actually Bluesky (bluesky_enabled=true).

## Root cause

The social-engagement channel is stored in a legacy-named field, `RawItem.reddit_score` / `ScoredStory.reddit_raw`. The Bluesky collector writes its engagement (likes+reposts+replies) into `reddit_score` (bluesky.py:109). Internally score.py already calls this the "social" signal (`_social_signal`, `weights["social"]`) — only the field name and two user-facing labels still said "Reddit":

- summarize.py system prompt: "Reddit discussion stats"; per-story line `reddit: N (score+comments)`. The model was handed the word "Reddit" for every story and narrated it.
- email.py meta line: "N upvotes+comments" — actually Bluesky reactions, not upvotes.

Ranking was correct throughout; this was purely mislabeling on output.

## Fix (relabel-only, source-neutral)

Chose source-neutral wording over hard-coding "Bluesky" — Reddit may come online via a third-party feed, at which point "Bluesky" would be the new lie, and both can feed the same channel.

- [x] summarize.py: prompt says "social engagement score", no platform name; added an explicit instruction not to name a platform or comment on how high/low the number is (kills the "limited ... engagement" editorializing too)
- [x] email.py: "N upvotes+comments" -> "N reaction(s)", pluralized
- [x] tests: prompt no longer contains "reddit"; email says "reactions" not "upvotes"; reaction-count pluralization

Internal field name `reddit_score`/`reddit_raw` left as-is by choice (scope: relabel outputs only). Renaming it to a social-neutral name across models/score/normalize/collectors is the durable root-cause fix — deferred as a follow-up.

## Summary of Changes

digest/summarize.py, digest/email.py, tests/test_summarize.py, tests/test_email.py. 111 tests pass. Verified by rendering the prompt (no "Reddit", explicit no-platform instruction) and the email meta line ("4 reactions · 2 outlets", "1 reaction · 1 outlet", "0 reactions").
