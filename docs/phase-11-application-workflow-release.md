# Phase 11: Application Workflow Release Review

Phase 11 Step 5 connects an approved preparation to a user-controlled employer-site handoff and a user-attested submission record.

## Workflow

1. A saved opportunity is matched and prepared.
2. The preparation is reviewed and explicitly approved.
3. `POST /api/v1/preparations/{id}/handoff` records the approved revision and source URL that the user is being shown.
4. The client may open that URL. A handoff does not create an application or an event.
5. `POST /api/v1/preparations/{id}/confirm-submission` requires the approved revision, resolved user-input questions, an idempotency key, and `user_confirmed_submission: true`.

Confirmation creates one `JobApplication` and one verified `APPLICATION_SUBMITTED` event atomically. Reusing an idempotency key returns the existing confirmation; a different confirmation for the same preparation is rejected. Preparation ownership, approval freshness, revision, CSRF, and trusted Origin checks remain enforced.

The confirmation is an attestation by the user, not independent proof from the employer. JobTrack does not submit forms, automate employer websites, fetch external pages, or store employer credentials. External confirmation references are optional user-provided metadata.

## Isolated Validation

- Database: `jobtrack_step5_test`
- Alembic revision: `d0e1f2a3b4c5 (head)`
- Focused handoff tests: 5 passed
- Backend regression tests: 221 passed
- Backend compilation: passed
- Frontend lint: passed, zero warnings
- Frontend production build: passed
- Git diff check: passed

## Concurrency

- Same-key simultaneous confirmations: passed
- Different-key simultaneous confirmations: passed
- Each scenario used two independent SQLAlchemy sessions and PostgreSQL backend connections.
- Final fresh-session assertions verified exactly one confirmation, application, and `APPLICATION_SUBMITTED` event.

## Safety Boundaries

- Handoff alone does not create an application.
- Submission confirmation requires explicit user attestation.
- No employer application is submitted automatically.
- Preparation approval is revision-specific.
- Cross-user access is denied.
- Unrelated working-tree modifications are preserved.

## Remaining Limitations

- No live employer-site submission has been performed.
- User attestation is not independent employer confirmation.
- The development database remains at `c9d0e1f2a3b4`; the new migration was applied only to the isolated database.
- Live Gmail OAuth callback walkthrough remains separately documented as not freshly observed.

## Release Decision

Ready for selective Step 5 commit, subject to staged-diff review.
