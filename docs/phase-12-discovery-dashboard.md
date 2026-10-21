# Phase 12: Discovery Dashboard

## Step 4 Scope

The authenticated React Discovery page browses the persisted Greenhouse catalog through `GET /api/v1/discovery/jobs`. It supports debounced text search, category, work-arrangement, sort, and pagination controls. Ranked results are computed by the existing matcher, and cards show score or explicit `NEEDS_PROFILE`, `INSUFFICIENT_EVIDENCE`, and eligibility states.

## API

- `GET /api/v1/discovery/sources` lists server-owned configured sources and freshness/error state.
- `POST /api/v1/discovery/sources/{id}/refresh` refreshes only an existing source row using its server-controlled board token. CSRF and authenticated session checks apply. Failed provider requests preserve the prior catalog snapshot.
- `POST /api/v1/discovery/jobs/{id}/save` idempotently imports one listing into the authenticated user's existing saved opportunities. It does not create an application or application event.

Refresh results report created, updated, unchanged, and observed counts. The source row lock from Step 2 serializes concurrent refreshes. No arbitrary outbound URL or board token is accepted from the browser.

## UI Behavior

The dashboard displays source freshness, refresh failures, loading and empty states, original employer links, work arrangement, availability, matching explanation, and a user-scoped Save Opportunity action. It intentionally has no Apply action. Duplicate saves are disabled while the request is active and after the job is saved.

## Validation

The isolated backend database `jobtrack_step5_test` is used for migrations and tests. Backend compilation, the existing suite, Alembic checks, frontend lint, and the production frontend build were run successfully. The frontend lint reports only non-blocking React hook warnings in the new page.

## Limitations

Refresh is synchronous and intended for explicit, bounded user actions. Scheduled refresh, stale-job policy, and background execution remain Phase 12 Step 5 concerns.
