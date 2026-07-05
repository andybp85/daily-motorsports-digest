---
# daily-motorsports-digest-5izk
title: Add clean Reddit-disable path; Reddit API now gated behind approval
status: completed
type: task
priority: normal
created_at: 2026-07-05T20:34:23Z
updated_at: 2026-07-05T20:39:25Z
---

Reddit's Responsible Builder Policy (late 2025) now requires manual approval for new OAuth tokens. Self-serve script-app creation at prefs/apps dead-ends in a captcha loop. Add a config flag to cleanly skip Reddit ingestion so the digest runs on RSS+GDELT, and draft an access-request ticket for later.

## Summary of Changes

- config: added `reddit_enabled` flag (default true); read from TOML in `load_config`.
- main: extracted `_collect_reddit(cfg)` — skips cleanly (returns []) when `reddit_enabled=false` or when any REDDIT_* cred is missing, printing a clear reason instead of constructing a doomed PRAW client.
- config.example.toml: documented `reddit_enabled` + the Responsible Builder Policy gate.
- README: rewrote the stale self-serve Reddit step; Reddit now marked optional with disable instructions.
- tests: two new cases covering both skip paths (57 passing).
- docs/reddit-api-access-request.md: context + ready-to-submit access-request ticket draft.

**Root cause:** Reddit Responsible Builder Policy (late 2025) gates all new API OAuth tokens behind manual approval. Self-serve prefs/apps creation dead-ends in a captcha loop -> policy link. Not a client/network/Pi-hole issue. Hobby/non-commercial approvals reportedly rare.
