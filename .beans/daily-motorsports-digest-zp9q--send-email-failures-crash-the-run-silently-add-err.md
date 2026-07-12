---
# daily-motorsports-digest-zp9q
title: send_email failures crash the run silently — add error handling
status: todo
type: bug
priority: normal
created_at: 2026-07-12T15:01:53Z
updated_at: 2026-07-12T15:01:53Z
---

digest/email.py send_email() has no error handling, and main.run() calls it (main.py ~line 108) inside a try/finally that only closes state. A boto3 SES failure (throttle, transient AWS error, creds/permission regression like the nepy sandbox bug) therefore propagates and crashes the whole run. On the systemd oneshot deploy that's a non-zero exit with the traceback buried in journalctl — no email, no visible signal. A silent 'no digest this morning' is exactly the failure mode that started this whole debugging session.

## Goal
Make a send failure loud and non-fatal-to-observability, without masking real problems.

## Approach (to design)
- Catch the SES/boto3 error at the send site, log it clearly (e.g. [digest] SEND FAILED: <err>), and exit non-zero so the unit still registers as failed.
- Consider: do NOT record_sent() the stories on send failure (currently record happens after send, so this is already correct — verify).
- Optional: surface failures out-of-band (the repo already has a key-expiry notify path; a send-failure notification is harder since the notifier is also SES — note that circular dependency).

## Todo
- [ ] Decide catch scope: only botocore ClientError/EndpointConnectionError vs broad
- [ ] TDD: test that a raising ses client is caught, logged, and record_sent is NOT called
- [ ] Implement in main.run (or a thin wrapper in email.py)
- [ ] Verify exit code semantics for the systemd unit (fail loud in journalctl)
