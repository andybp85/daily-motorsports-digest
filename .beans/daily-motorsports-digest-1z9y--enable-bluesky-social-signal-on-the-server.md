---
# daily-motorsports-digest-1z9y
title: Enable Bluesky social signal on the server
status: completed
type: task
priority: normal
created_at: 2026-07-11T22:44:21Z
updated_at: 2026-07-12T14:57:47Z
---

The Bluesky enrichment (bean qzme) is merged to main and degrades cleanly while disabled. To actually turn it on for the daily digest, on the SERVER:

- [x] config.toml: set bluesky_enabled = true
- [ ] .env: set BSKY_HANDLE=<domain> (the account handle or email — NOT the app-password label)
- [ ] .env: set BSKY_APP_PASSWORD to a valid app password for that account (bsky.app → Settings → App Passwords; read-only)
- [x] Verify: Pi dry-runs show de-flattened scores, no [bluesky] auth errors

Note: the local dev .env currently has BSKY_HANDLE set to the app-password label 'andys-motosport-digest' (invalid) — fix locally too if running the digest here.

Scope reminder: signal is F1-heavy; IndyCar has ~no Bluesky volume so those stories score ~0 (neutral) by design.

## Summary of Changes

Deployed and verified on the Pi 2026-07-12. bluesky_enabled=true, BSKY_HANDLE/BSKY_APP_PASSWORD set in .env. Dry-runs show de-flattened scores (0.79→0.38 spread) with no [bluesky] auth errors. Real send succeeded ([digest] sent 8 stories) and systemd timer is armed for Mon 06:00 EDT. Bluesky social signal is live in production.
