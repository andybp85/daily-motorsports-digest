---
# daily-motorsports-digest-wqi3
title: Bare "F2" substring-matches "F2A" — Visa Bulletin story leaked into digest
status: completed
type: bug
priority: normal
created_at: 2026-07-22T22:44:02Z
updated_at: 2026-07-22T22:45:47Z
---

A State Department Visa Bulletin story ("...Visa Bulletin F2A cutoff") reached the 2026-07-22 digest labeled Formula 2.

## Root cause
classify_series() (normalize.py) matches terms by naive substring (`term.lower() in low`). The f2 series has a bare `"F2"` term, which is a substring of `"F2A"`. Visa Bulletin categories are literally F1/F2A/F2B/F3 — GDELT's f1 keyword "F1" matched the visa category in the article body, the row was returned, and is_relevant() re-checked the title where "F2" hit "F2A". Registry order (f2 before f1) labeled it Formula 2.

Distinct from [[daily-motorsports-digest-9b35]] (ambiguous surnames) and [[daily-motorsports-digest-lm78]] (semantic "Grand Prix"): this is a substring-vs-token boundary failure, the residual the config comment flagged as 'bare F2/F3'.

## Fix
- [x] Whole-token matching in classify_series (word boundaries) so "F2" matches the token F2, not the substring in F2A/F20
- [x] Regression test: the F2A visa headline must be rejected; legit "F2"/"F3" headlines must still classify
- [x] Update models.py term doc (substring-matched -> whole-token) and config comment
- [x] Reconcile config.example.toml if touched

## Summary of Changes

`classify_series()` now matches terms on whole-token (`\b` word) boundaries via `_term_in_title()` instead of naive `in` substring, so the bare `F2` term matches the token `F2`, not the substring in `F2A`/`F20`. All shipped terms start/end with word characters, so `\b` is well-defined; `re.escape` keeps punctuation (O`Ward, E-Prix) literal. Kept bare `F2`/`F3` — legit `F2 sprint...` headlines still classify.

Tests: reproduced the exact leak (RED) in `test_normalize.py` (token vs substring) and `test_shipped_config_terms.py` (real F2A headline in the reject set), then fixed (GREEN). 113 passed. Updated `models.py` term doc and the registry comment in both configs.

Residual (not fixed, by design): a visa headline whose *title* contains a bounded bare token like `F1`/`F2` would still classify — same accept-small-residue tradeoff as [[daily-motorsports-digest-lm78]]. The reported instance (title `...F2A cutoff`, no bounded f-token) is fully closed.
