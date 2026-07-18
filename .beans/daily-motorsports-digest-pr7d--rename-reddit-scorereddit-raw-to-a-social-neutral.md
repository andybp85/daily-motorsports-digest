---
# daily-motorsports-digest-pr7d
title: Rename reddit_score/reddit_raw to a social-neutral field name
status: todo
type: task
priority: low
created_at: 2026-07-18T16:35:06Z
updated_at: 2026-07-18T16:35:06Z
parent: daily-motorsports-digest-z6pt
---

Follow-up to [[daily-motorsports-digest-edx5]]. The social-engagement signal is stored in `RawItem.reddit_score` / `RawItem.reddit_comments` / `ScoredStory.reddit_raw`, but the channel is source-agnostic — Bluesky feeds it today, Reddit would too if enabled, and score.py already calls the concept "social". The name is a leftover from when Reddit was the only source.

edx5 fixed the user-facing labels (summary prompt + email) source-neutrally, so nothing lies to the reader anymore. This is the deeper root-cause fix: rename the field so nobody reads `reddit_raw` in code and believes the number is Reddit.

## Scope
- [ ] models.py: rename reddit_score/reddit_comments (RawItem), reddit_raw (ScoredStory) — pick names (social_score/social_comments/social_raw, or collapse to one social_engagement)
- [ ] Update writers: collect/reddit.py, collect/bluesky.py
- [ ] Update readers: score.py (_social_signal), email.py, summarize.py, normalize.py (carries the fields through)
- [ ] Update tests referencing the old names
- [ ] Decide whether Reddit still needs two sub-fields (score + comments) while Bluesky lumps into one — informs whether to keep two fields or one

Mechanical but wide (touches ~7 modules + tests). Low priority — purely internal clarity, no behavior change.
