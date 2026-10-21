# Phase 12 Discovery Release Review

## Implementation

- Discovery catalog migration head: `a3b4c5d6e7f8`.
- Scheduled refresh is disabled by default with a six-hour interval, fifteen-minute expiring lease, and maximum two source claims per run.
- Workers claim sources with PostgreSQL row locks, commit the lease before network I/O, and verify the ownership token before completion.
- The scheduler reuses the Greenhouse adapter and transactional ingestion service. Provider failures preserve the previous catalog snapshot and record failure state.
- No scheduler or discovery action creates applications or `APPLICATION_SUBMITTED` events.

## Browser Verification

The frontend source is served successfully by the existing Vite process on `localhost:5175` (`HTTP 200`). A fresh launch on the occupied development port was not used; the existing QA frontend was preserved.

The active backend on `localhost:8000` remains a separate older Uvicorn instance and was not terminated. The QA backend was restarted separately on `localhost:8004` with `DB_NAME=jobtrack_step5_test`; its OpenAPI schema includes the candidate-profile and discovery routes, and Alembic is at `a3b4c5d6e7f8`.

The frontend uses `VITE_API_BASE_URL=http://localhost:8004`. CORS was corrected to allow `PUT`; a live preflight from `http://localhost:5175` returned `200` with `Access-Control-Allow-Origin`, `PUT`, credentials, and `X-CSRF-Token` permitted. Google OAuth was verified with the isolated QA account `vamshiboston@gmail.com`.

The guarded QA seed script at `backend/scripts/seed_qa_discovery.py` requires `QA_SEED_ENABLED=true`, verifies `current_database()` is `jobtrack_step5_test`, uses the existing `DiscoverySource` and `DiscoveredJob` models, and is idempotent for the `qa_fixture` source. It created these synthetic records only: Example Systems / Oracle CPQ Developer (remote, United States), Demo Robotics / Java Backend Engineer (hybrid, Boston, MA), Sample Analytics / Data Engineer (onsite, Boston, MA), Fictional Technologies / Associate Software Engineer (unknown location and arrangement), and Test Cloud Inc. / Python Backend Developer (remote, Massachusetts). No live provider request was made.

Populated Discovery verification completed against thirteen roles. Location `Boston` returned six Boston-only records; arrangement `Unknown` returned only Fictional Technologies / Associate Software Engineer. Clearing filters showed twelve cards on page one, and page two showed only `Data Engineer` (`13-13 of 13`). Changing Location on page two reset to the first filtered page. Remote results preserved geographic restrictions.

The candidate profile editor saved the synthetic QA profile successfully and displayed confirmed revision `1`; profile values persisted through navigation. Discovery then displayed numeric scores and confirmed matched skills where evidence was sufficient, while insufficient-evidence cards remained explicitly labeled. The fixed page size remains 12. Blocking the refresh request in the browser produced `Failed to fetch` while preserving all 12 visible job cards; removing the block restored normal operation. Controlled provider failure and scheduler persistence tests remain separately covered by backend tests. Applications and submission events remained zero, and the existing saved opportunity rendered as disabled `Saved` on repeat save.

## Validation

- Backend: `233 passed`.
- Focused discovery/scheduler/matching tests: `14 passed`.
- Compilation: passed.
- Alembic current/check: passed after constraint-name alignment.
- Frontend production build: passed.
- Frontend lint: passed with no warnings after preserving the pagination offset in the discovery loading effect.

## Final Phase 12 Acceptance

### Verified

- QA backend and authenticated frontend connected.
- CORS PUT preflight: `200`.
- Candidate profile revision `1` persisted.
- Boston filter: 6 roles.
- Unknown arrangement: 1 expected role.
- Pagination: 12 + 1 roles.
- Filter reset from page 2: passed.
- Numeric ranking and matched evidence: passed.
- Applications created: 0.
- Submission events created: 0.
- Backend tests: 233 passed.
- Frontend lint and build: passed.
- Python compilation: passed.
- Alembic: clean.
- Blocked refresh preserved existing cards and displayed a request error.

### Refresh Failure Handling

- Backend failure preservation: passed automated tests.
- Frontend request failure: passed with controlled browser request blocking.

### Release Boundary

- Development backend on `8000` preserved.
- QA backend on `8004` verified.
- Unrelated worktree edits preserved.
- Intended Phase 12 files staged separately from unrelated changes.

### Release Decision

Functional acceptance passed. The Phase 12 implementation is ready for a selective commit.

## Limitations

The scheduler is provided as an explicit worker module and remains disabled during QA. No live provider or employer application submission was performed.
