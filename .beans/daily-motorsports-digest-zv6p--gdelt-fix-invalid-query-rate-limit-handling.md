---
# daily-motorsports-digest-zv6p
title: 'GDELT: fix invalid query + rate-limit handling'
status: completed
type: bug
created_at: 2026-07-10T13:22:30Z
updated_at: 2026-07-10T13:22:30Z
---

GDELT contributed 0 stories in the first Pi dry-run. Investigated after deploy.

## Root causes
1. build_keyword_list ORed ~34 series/team/driver terms into one query -> GDELT 'query too short or too long'.
2. fetch_gdelt fired 4 calls back-to-back (article+timeline x 2 series) -> GDELT ~1-req/5s throttle -> empty-message RateLimitError.

## Fix (commit 096180d)
- Query GDELT with series terms only; is_relevant() applies teams/drivers/anchors downstream. Confirmed: series-only article_search returned 250 rows.
- Wrap searches in _search_with_retry (linear backoff, catches gdeltdoc.errors.RateLimitError).

## Verification note
Post-fix verification is blocked by a real IP-level 429 (confirmed via raw urllib: 'HTTP Error 429: Too Many Requests') from ~15 test calls during diagnosis. 18-min cooldown did not clear it. Not a code defect; self-clears over time. Daily run makes only 4 calls, well under the limit, and GDELT is non-blocking (RSS carries the digest; failed series -> spike=1.0).

## Summary of Changes
gdelt.py: build_keyword_list -> series-only; added _search_with_retry; fetch_gdelt uses it. test_gdelt.py: updated build_keyword_list contract test. 64 tests pass.
