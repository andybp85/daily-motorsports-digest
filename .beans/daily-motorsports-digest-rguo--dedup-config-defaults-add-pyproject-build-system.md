---
# daily-motorsports-digest-rguo
title: Dedup Config defaults + add pyproject [build-system]
status: todo
type: task
priority: deferred
created_at: 2026-07-03T21:01:21Z
updated_at: 2026-07-03T21:01:44Z
parent: daily-motorsports-digest-ch7c
---

Default values are duplicated between Config dataclass field defaults and load_config's data.get(key, default) calls - foot-gun if a field is added to only one place. Also pyproject.toml has no [build-system] table (app runs via python -m, so packages.find is unused anyway).
