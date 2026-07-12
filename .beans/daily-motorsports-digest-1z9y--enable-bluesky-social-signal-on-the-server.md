---
# daily-motorsports-digest-1z9y
title: Enable Bluesky social signal on the server
status: todo
type: task
priority: normal
created_at: 2026-07-11T22:44:21Z
updated_at: 2026-07-11T22:44:21Z
---

The Bluesky enrichment (bean qzme) is merged to main and degrades cleanly while disabled. To actually turn it on for the daily digest, on the SERVER:

- [ ] config.toml: set bluesky_enabled = true
- [ ] .env: set BSKY_HANDLE=<domain> (the account handle or email — NOT the app-password label)
- [ ] .env: set BSKY_APP_PASSWORD to a valid app password for that account (bsky.app → Settings → App Passwords; read-only)
- [ ] Verify: a dry-run shows no [bluesky] error lines and de-flattened scores (local test went from flat 0.511 to a 0.462–0.763 spread)

Note: the local dev .env currently has BSKY_HANDLE set to the app-password label 'andys-motosport-digest' (invalid) — fix locally too if running the digest here.

Scope reminder: signal is F1-heavy; IndyCar has ~no Bluesky volume so those stories score ~0 (neutral) by design.
