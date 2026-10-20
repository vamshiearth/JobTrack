# JobTrack - Phase 8 Gmail Integration Architecture

## Status

Architecture and security design only.
No Gmail access, tokens, synchronization, or application updates are enabled by this document.

## Goal

Connect Gmail with explicit user consent to identify recruitment communications, associate messages with saved applications, and propose reviewed updates.

## Prerequisite

Verify existing Google browser sign-in and logout before live Gmail authorization.

## Authorization

JobTrack sign-in and Gmail authorization are independent.

Identity scopes:

- `openid`
- `email`
- `profile`

Initial Gmail scope:

- `https://www.googleapis.com/auth/gmail.metadata`

Do not request Gmail send, modify, compose, or full mailbox-access scopes.

Request `gmail.readonly` only in a future, separately approved feature requiring message bodies.

Both metadata and readonly are restricted scopes. Review Google OAuth verification, user-data policy, and applicable security assessment requirements before public release.

## Gmail OAuth Security

- Require a current authenticated JobTrack session.
- Require trusted origin and CSRF protection to initiate a connection-changing workflow.
- Generate state, nonce, and PKCE material as applicable.
- Bind the pending Gmail authorization transaction to the initiating JobTrack user and browser.
- Validate the returned OAuth state and transaction age.
- Consume the transaction only once.
- Verify the Google account identity independently.
- Confirm the returned permissions match expectations.
- Do not silently link an unexpected Google account.
- Never expose access or refresh tokens to React.
- Handle user denial without changing existing grants.

## Credential Storage

- Reuse the existing `gmail_connections` table.
- Review its actual schema before modifying it.
- Encrypt refresh tokens with authenticated encryption.
- Manage encryption keys separately from PostgreSQL.
- Never log OAuth codes, tokens, or encryption keys.
- Record scope, expiry, status, and user ownership.
- Support token rotation and revocation.
- Implement explicit Gmail disconnect.

## Sync State

- Reuse `gmail_sync_states`.
- Begin with a bounded initial synchronization.
- Save permitted message IDs and metadata.
- Do not retrieve email bodies or attachments.
- Use Gmail `history.list` for incremental changes.
- Handle expired history cursors with safe resync.
- Deduplicate messages by connection and message ID.
- Advance cursors only after successful persistence.
- Do not sync disconnected accounts.
- Expose recoverable sync errors without leaking data.

## Restricted Scope Limitations

`gmail.metadata` does not provide message bodies. The Gmail `messages.list` `q` search parameter is unavailable with `gmail.metadata`.

Initial classification must use permitted headers and other available metadata, not assume access to bodies.

## Review Before Updating

- Reuse `review_items` where compatible.
- Link each suggestion to evidence and a candidate application where a defensible match exists.
- Explain ambiguity instead of inventing certainty.
- Keep suggestions pending until explicit user action.
- Rejected suggestions do not modify applications.
- Approval invokes the existing validated event service.
- Preserve event ordering and idempotency protections.
- Never automatically send emails or job applications.

## Data Minimization and Privacy

- Retain only data needed for recruitment tracking.
- Never fetch attachments by default.
- Define configurable retention before live sync.
- Provide disconnect and data-removal controls.
- Prevent cross-user connection, message, and review-item access.
- Do not reuse Gmail content for unrelated purposes.

## Proposed API Surface

```text
GET  /api/v1/gmail/connection
POST /api/v1/gmail/connect
GET  /api/v1/gmail/callback
POST /api/v1/gmail/disconnect
POST /api/v1/gmail/sync
GET  /api/v1/gmail/sync-status

GET  /api/v1/review-items
POST /api/v1/review-items/{id}/approve
POST /api/v1/review-items/{id}/reject
```

These are proposed contracts, not implemented endpoints.

## Required Tests

- Unauthenticated connection attempts rejected.
- CSRF and untrusted-origin requests rejected.
- Missing, invalid, expired, and replayed OAuth state rejected.
- OAuth transaction remains bound to initiating user.
- Unexpected mailbox/account mismatch handled safely.
- Grant denial leaves connection state unchanged.
- Tokens remain encrypted at rest and absent from responses.
- Credential expiration and revocation handled.
- Duplicate sync messages are idempotent.
- Invalid history cursor triggers safe resync.
- Failed persistence never advances sync cursor.
- Disconnected connections cannot sync.
- Cross-user connection, message, and review access rejected.
- Review rejection never changes application history.
- Review approval uses existing event validation.

## Known Limitations

- Google browser authentication remains unverified.
- Gmail OAuth credentials are not yet configured.
- Gmail API synchronization is not implemented.
- Email classification is not implemented.
- Automated review is not implemented.
- Public OAuth verification and restricted-scope compliance are not yet completed.

## Next Step

Audit the existing Gmail ORM models and implement secure connection configuration and credential storage.
