---
# daily-motorsports-digest-kv7o
title: 'Harden misc: extra-dict aliasing, code-fence regex, %-d, state test hygiene'
status: todo
type: task
priority: deferred
created_at: 2026-07-03T21:01:21Z
updated_at: 2026-07-03T21:01:44Z
parent: daily-motorsports-digest-ch7c
---

Grab-bag of reviewer minors: (1) normalize_items copies extra by reference (extra=it.extra) - use dict(it.extra) if a caller ever mutates extra; (2) summarize code-fence regex fragile to leading whitespace (parse failure degrades to titles, so low risk); (3) email.py %-d strftime is POSIX-only (fine for Pi/macOS target); (4) state.py tests close() at body end not try/finally, and sent_stories has no index (fine at scale).
