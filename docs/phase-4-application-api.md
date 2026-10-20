# JobTrack - Phase 4 Application APIs

## Status

Complete after final verification.

## Implemented Endpoints

- `POST /api/v1/applications`
- `GET /api/v1/applications`
- `GET /api/v1/applications/{id}`
- `PATCH /api/v1/applications/{id}`
- `DELETE /api/v1/applications/{id}`
- `GET /api/v1/applications/{id}/events`
- `POST /api/v1/applications/{id}/events`

## Features

- Pydantic request validation
- Ownership-scoped services
- Transactional application creation
- Initial application timeline events
- Manual recruitment progress tracking
- Assessment and interview prerequisites
- Idempotent manual event submission
- Closed application protection
- Application search and filters
- Pagination and stable sorting
- Standardized API error responses

## Security

All application endpoints currently deny requests without authentication.

Tests override the authentication dependency using trusted test identities.

Production authentication remains to be implemented before end-user access.

## Deferred Work

- Real Google OAuth and session management
- UI integration after authentication
- Concurrency and simultaneous-write tests
- Timeline corrections and reopening
- Gmail email synchronization
- Gmail token encryption
- Additional application ownership checks for cross-entity email associations

## Database

Alembic revision: `f1a2b3c4d5e6`

## Next Phase

Phase 5 - React Dashboard Foundation.
