---
# daily-motorsports-digest-guff
title: Consider team/driver->series fallback in classify_series
status: todo
type: task
priority: deferred
created_at: 2026-07-03T21:01:21Z
updated_at: 2026-07-03T21:01:44Z
parent: daily-motorsports-digest-ch7c
---

classify_series infers series only from series_f1/series_indycar keyword lists, not teams/drivers. A title like 'Ferrari upgrade' or 'Palou pole' resolves to '' -> spike signal (0.15) goes neutral. GDELT items now carry series (fixed), but RSS-discovery items with no series word still miss. During the 2-week calibration window, watch how often story.series logs as '' - if a large fraction, add the team/driver->series fallback.
