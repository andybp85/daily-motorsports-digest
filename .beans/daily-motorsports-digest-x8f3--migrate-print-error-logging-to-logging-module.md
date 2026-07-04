---
# daily-motorsports-digest-x8f3
title: Migrate print() error logging to logging module
status: todo
type: task
priority: deferred
created_at: 2026-07-03T21:01:21Z
updated_at: 2026-07-03T21:01:44Z
parent: daily-motorsports-digest-ch7c
---

All collectors (rss/gdelt/reddit), summarize.py, and main.py use print() for error/degradation reporting. Works under systemd/journald but a proper logger routes/filters better. Codebase-wide change - do in one sweep, not piecemeal.
