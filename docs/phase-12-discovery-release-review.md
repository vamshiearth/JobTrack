# Phase 12 Discovery Release Review

## Implementation

- Discovery catalog migration head: `a3b4c5d6e7f8`.
- Scheduled refresh is disabled by default with a six-hour interval, fifteen-minute expiring lease, and maximum two source claims per run.
- Workers claim sources with PostgreSQL row locks, commit the lease before network I/O, and verify the ownership token before completion.
- The scheduler reuses the Greenhouse adapter and transactional ingestion service. Provider failures preserve the previous catalog snapshot and record failure state.
- No scheduler or discovery action creates applications or `APPLICATION_SUBMITTED` events.

## Browser Verification

The frontend source is served successfully by the existing Vite process on `localhost:5173` (`HTTP 200`). A fresh launch from `frontend` with `--strictPort` reported `Port 5173 is already in use`; the listener is a Node process owned by this workspace environment and was not terminated.

The active backend on `localhost:8000` is PID `20216`, running an older Uvicorn instance whose OpenAPI schema contains no discovery paths. It was left running because it was not safe to terminate an unrelated/stale process. The current backend was started separately on `localhost:8004` with `DB_NAME=jobtrack_step5_test`; its OpenAPI schema includes all four discovery routes, and the database identity plus Alembic head were verified as `jobtrack_step5_test` and `a3b4c5d6e7f8`.

The frontend was started separately on `localhost:5175` with `VITE_API_BASE_URL=http://localhost:8004`. CORS was corrected to use the existing trusted-origin settings, and the QA backend was run with `http://localhost:5175` as a temporary trusted origin. Google OAuth was verified with the isolated QA account `vamshiboston@gmail.com`; the callback returned through `localhost:8004`, the authenticated Discovery page loaded, and logout returned to the sign-in screen.

The guarded QA seed script at `backend/scripts/seed_qa_discovery.py` requires `QA_SEED_ENABLED=true`, verifies `current_database()` is `jobtrack_step5_test`, uses the existing `DiscoverySource` and `DiscoveredJob` models, and is idempotent for the `qa_fixture` source. It created these synthetic records only: Example Systems / Oracle CPQ Developer (remote, United States), Demo Robotics / Java Backend Engineer (hybrid, Boston, MA), Sample Analytics / Data Engineer (onsite, Boston, MA), Fictional Technologies / Associate Software Engineer (unknown location and arrangement), and Test Cloud Inc. / Python Backend Developer (remote, Massachusetts). No live provider request was made.

Populated Discovery verification completed: the unfiltered catalog showed five roles; `Oracle CPQ` returned only Example Systems; Java returned Demo Robotics; Data Engineer returned Sample Analytics; onsite returned Sample Analytics; hybrid returned Demo Robotics; remote returned Example Systems and Test Cloud Inc.; nonexistent search showed the genuine empty state; and clear-all returned all five. The remote cards preserved distinct `United States` and `Massachusetts` locations. The UI search covers title/employer only, so `Boston` returned no rows; the UI has no location or `UNKNOWN` arrangement option, so those browser checks were unavailable rather than passed.

Every card displayed `NEEDS_PROFILE` with no fabricated score. The QA account has no candidate profile (`GET /api/v1/candidate-profile` returned `404`), and the current UI has no profile editor, so numeric ranking and deterministic scored ordering were not tested. The UI uses a fixed limit of 12 and exposes no page-size selector; with five jobs it renders one page, so the requested 2/2/1 pagination distribution is not applicable. Controlled provider failure and scheduler persistence tests passed backend-only (`9 passed`), but browser refresh-error presentation was not injected. A direct QA database check reported five discovered jobs, one saved opportunity, zero `job_applications`, and zero `application_events`; Oracle's second save state rendered as disabled `Saved`, preserving one opportunity.

## Validation

- Backend: `233 passed`.
- Scheduler lease tests: `3 passed`.
- Compilation: passed.
- Alembic current/check: passed after constraint-name alignment.
- Frontend production build: passed.
- Frontend lint: passed with no warnings after moving filter page resets to filter events and keeping source synchronization non-urgent.

## Limitations

The scheduler is provided as an explicit worker module and remains disabled during QA. Location/unknown browser controls, numeric ranking, 2/2/1 pagination, and browser-injected refresh failure remain unverified or unavailable in the current UI. No live provider or employer application submission was performed.
