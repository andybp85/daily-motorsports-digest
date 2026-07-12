---
# daily-motorsports-digest-d0fh
title: GDELT hang blocks digest — no email sent
status: completed
type: bug
priority: high
created_at: 2026-07-11T15:39:33Z
updated_at: 2026-07-11T15:44:34Z
---

gdeltdoc calls requests.get() with no timeout (api_client.py:162). When GDELT stalls the connection, fetch_gdelt hangs forever; _search_with_retry only catches RateLimitError, not hangs. On the systemd oneshot deploy the service is killed on start-timeout before the email step runs -> no digest. Intermittent (depends on GDELT stalling), matching 'no email this morning'.

## Todo
- [x] Failing test: hanging GDELT client must not hang fetch_gdelt
- [x] Bound each GDELT HTTP call with a hard timeout; degrade like other GDELT failures
- [x] Run full test suite green
- [x] Verify end-to-end dry-run completes

## Summary of Changes

Root cause: gdeltdoc api_client.py calls requests.get() with no timeout; a stalled GDELT connection hung fetch_gdelt forever. _search_with_retry only caught RateLimitError, so a hang never triggered retry/fallback. On the systemd oneshot deploy the service is killed on start-timeout before the email step runs, so no digest is sent. Reproduced locally: the dry-run hung indefinitely on GDELT.

Fix (digest/collect/gdelt.py): wrap each GDELT HTTP call in a SIGALRM-based _time_limit (default 30s/call). A timeout raises GdeltTimeout, which propagates to the existing per-series except -> logs [gdelt] failed, neutral spikes (1.0), no articles for that series. The digest continues on RSS, matching the existing graceful-degradation design. Added a timeout param to fetch_gdelt/_search_with_retry for testability.

Test: test_fetch_gdelt_survives_a_hanging_search injects a client whose searches sleep; asserts fetch_gdelt returns ([], neutral spikes) fast instead of hanging. Full suite 68 passed; end-to-end dry-run now completes (exit 0, ranks 8 stories) after GDELT times out cleanly.

Not committed yet.
