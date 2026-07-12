---
# daily-motorsports-digest-nepy
title: 'SES AccessDenied: server IAM user can''t ses:SendEmail'
status: todo
type: bug
priority: critical
created_at: 2026-07-11T16:08:35Z
updated_at: 2026-07-11T18:11:30Z
---

The IAM user the server runs as (arn:aws:iam::<ACCOUNT_ID>:user/motorsports-digest, creds in .env / systemd EnvironmentFile) gets AccessDenied on ses:SendEmail for identity <recipient-email>:

  botocore ClientError (AccessDenied) calling SendEmail: User arn:aws:iam::<ACCOUNT_ID>:user/motorsports-digest is not authorized to perform ses:SendEmail on resource arn:aws:ses:us-east-1:<ACCOUNT_ID>:identity/<recipient-email>

This fails deterministically, so on the server the digest would crash at the send step even when the pipeline completes — a likely cause of missed morning digests, independent of the GDELT hang (bean d0fh).

## How it surfaced
Local send with the repo .env creds (= server's IAM user) hit AccessDenied. A local send using the default AWS profile (user/andy) succeeded, which is why a titles-only digest did reach the inbox today. So the two identities differ in SES permissions.

## Notes / hypotheses (needs Andy's AWS access to confirm)
- IAM policy for user/motorsports-digest lacks ses:SendEmail on the sender identity (motorsports-digest@<domain>) and/or the recipient identity. Note the denied *resource* is the recipient identity (<recipient-email>), suggesting a resource-scoped policy or SES sandbox (both sender+recipient must be verified).
- SES memory says this was configured/working, so something changed: policy tightened, identity verification lapsed, or key rotated to a less-privileged user.
- send_email() has no error handling — SendEmail failure crashes the whole run (main.py:90). Even after IAM is fixed, consider catching/logging so a send error is visible, not a silent systemd failure.

## Todo
- [x] Confirm on the server which IAM user + creds are actually in use (user/motorsports-digest, from .env)
- [x] Grant ses:SendEmail to user/motorsports-digest — added recipient identity to policy Resource (applied)
- [x] Verify a real send succeeds with the server creds — MessageId 0100019f525fb7ef… returned 2026-07-11
- [ ] Consider wrapping send_email so failures log instead of crashing silently

## Diagnosis (confirmed 2026-07-11 via user/andy)

Account is in the SES **sandbox** (ProductionAccessEnabled=False, SendingEnabled=True). Inline policy 'ses-send' on user/motorsports-digest allowed ses:SendEmail/SendRawEmail only on Resource identity/<domain> (sender), with condition ses:FromAddress=motorsports-digest@<domain>. In the sandbox SES authorizes SendEmail against the From identity AND each recipient identity, so sending to identity/<recipient-email> was denied — exactly the ARN in the error. Identities themselves are fine (recipient is verified; a send via user/andy succeeded).

## Fix (least-privilege, keeps sandbox)
Add the recipient identity to the policy Resource list:

  Resource: [
    arn:aws:ses:us-east-1:<ACCOUNT_ID>:identity/<domain>,
    arn:aws:ses:us-east-1:<ACCOUNT_ID>:identity/<recipient-email>
  ]

Apply (put-user-policy overwrites the same-named inline policy):
  aws iam put-user-policy --user-name motorsports-digest --policy-name ses-send --policy-document file://ses-send.json

Durable alternative: request SES production access to leave the sandbox (then recipient-identity authorization/verification is unnecessary). Overkill for a single fixed recipient.
