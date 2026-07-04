---
# daily-motorsports-digest-3mol
title: Tighten type annotations to project's precise-type rule
status: todo
type: task
priority: deferred
created_at: 2026-07-03T21:01:21Z
updated_at: 2026-07-03T21:01:44Z
parent: daily-motorsports-digest-ch7c
---

fetch_gdelt(..., client=None) is unannotated (awkward because gdeltdoc import is function-local); several dict/list[dict] params could be dict[str, list[str]] etc. Project python rules prefer precise types. Style-only, no runtime effect.
