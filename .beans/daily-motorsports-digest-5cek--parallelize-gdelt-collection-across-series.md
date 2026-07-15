---
# daily-motorsports-digest-5cek
title: Parallelize GDELT collection across series
status: todo
type: task
priority: normal
created_at: 2026-07-15T16:37:13Z
updated_at: 2026-07-15T16:37:13Z
---

GDELT calls are made sequentially, one per series, each with a 30s timeout (digest/collect/gdelt.py, driven by cfg.series). With the multi-series expansion the registry grew to 10 series, so a full collection runs ~5 min and a single slow/hung series can starve the rest — observed f1+indycar GDELT timeouts on both the 2026-07-15 dry-run and the real afternoon run (RSS carried the digest to a full 15 both times, so it degraded gracefully).

## Why
Sequential 10x30s worst-case (~300s) makes the daily run slow and fragile as more series are added. GDELT flakiness on any one series shouldn't delay or endanger the others.

## Todo
- [ ] Fan out per-series GDELT calls concurrently (thread pool or async), preserving the existing 30s per-call timeout
- [ ] Aggregate results + spike ratios; a failed/timed-out series degrades to empty (current behavior) without blocking others
- [ ] Bound concurrency sensibly (GDELT rate limits) and keep output order deterministic
- [ ] Tests: partial-failure aggregation, timeout isolation

## Context
Surfaced during the tiered-weighting deploy (bean kcdf). Measure before/after per Pike's rules — confirm sequential collection is the actual bottleneck.
