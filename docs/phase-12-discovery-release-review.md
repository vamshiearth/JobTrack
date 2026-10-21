# Phase 12 Discovery Release Review

## Implementation

- Discovery catalog migration head: `a3b4c5d6e7f8`.
- Scheduled refresh is disabled by default with a six-hour interval, fifteen-minute expiring lease, and maximum two source claims per run.
- Workers claim sources with PostgreSQL row locks, commit the lease before network I/O, and verify the ownership token before completion.
- The scheduler reuses the Greenhouse adapter and transactional ingestion service. Provider failures preserve the previous catalog snapshot and record failure state.
- No scheduler or discovery action creates applications or `APPLICATION_SUBMITTED` events.

## Browser Verification

The frontend source is served successfully by the existing Vite process on `localhost:5173` (`HTTP 200`). A fresh launch from `frontend` with `--strictPort` reported `Port 5173 is already in use`; the listener is a Node process owned by this workspace environment and was not terminated.

The active backend on `localhost:8000` returns healthy status, but its OpenAPI schema contains no discovery paths, indicating it is an older server process. A fresh isolated QA server could not bind because port `8000` was already occupied. Therefore authenticated browser acceptance against the new discovery API is not claimed. The QA database itself is migrated and verified at `a3b4c5d6e7f8`.

## Validation

- Backend: `233 passed`.
- Scheduler lease tests: `3 passed`.
- Compilation: passed.
- Alembic current/check: passed after constraint-name alignment.
- Frontend production build: passed.
- Frontend lint: passed with one non-blocking `react(set-state-in-effect)` warning in the Discovery page.

## Limitations

The scheduler is provided as an explicit worker module and remains disabled until `DISCOVERY_SCHEDULER_ENABLED=true` is configured. Browser acceptance, live Greenhouse refresh, and scheduled provider integration remain environment-dependent because the active backend process predates the Step 4 routes. No live provider or employer application submission was performed.
