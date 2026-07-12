---
# daily-motorsports-digest-s9sk
title: 'GDELT hangs on IPv6-broken networks: prefer IPv4 in-process'
status: completed
type: bug
priority: high
created_at: 2026-07-12T13:02:39Z
updated_at: 2026-07-12T13:04:29Z
---

On the Pi deploy, IPv6 to api.gdeltproject.org black-holes (curl -6 fails, curl -4 works). Python's requests/urllib3 walk getaddrinfo in order and stall on the IPv6 attempt, tripping the 30s per-call timeout (bean d0fh) for both series — GDELT contributes nothing and adds 60s/run. /etc/gai.conf IPv4-preference did NOT reach Python's resolver. A getaddrinfo monkeypatch forcing IPv4-only in-process returned 29 rows in 14s, confirming root cause. Fix: scope an IPv4-first getaddrinfo ordering around the GDELT calls (mirrors the _time_limit context-manager pattern). Keeps IPv6 as fallback for hosts where IPv4 is the broken path. The d0fh timeout stays as the safety net.

## Summary of Changes

Added `_prefer_ipv4()` context manager in digest/collect/gdelt.py (mirrors the `_time_limit` pattern): wraps socket.getaddrinfo to sort AF_INET rows first, keeping IPv6 as fallback. Scoped per-call in `_search_with_retry` alongside the timeout. 2 regression tests (ordering + resolver restoration). 85 tests pass, ruff clean. Verified in-process on the Pi: IPv4-forced gdeltdoc call returned 29 rows in 14s where dual-stack timed out at 30s.
