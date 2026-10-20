# JobTrack - Phase 3 Database Implementation

## Status

Phase 3: Complete after final validation.

## Database

- Engine: PostgreSQL 18
- Database: jobtrack_db
- Application role: jobtrack_user
- ORM: SQLAlchemy 2.x
- Migration tool: Alembic

## Database Tables

1. users
2. gmail_connections
3. gmail_sync_states
4. email_messages
5. job_applications
6. application_events
7. review_items

## Migration

Initial revision: d4d0b009600b

## Validated Features

- PostgreSQL connectivity
- SQLAlchemy sessions
- UUID primary keys
- Foreign-key constraints
- Unique constraints
- Application status constraints
- Timeline event storage
- Duplicate Gmail message prevention
- Transaction rollback
- Application deletion behavior
- Schema audit tests

## Security

- Dedicated non-superuser database account
- Credentials stored in Git-ignored backend/.env
- No credentials in frontend configuration
- Parameterized SQLAlchemy queries

## Deferred Security Requirements

- User-scoped application queries
- Cross-user ownership validation
- Authentication and session management
- Encrypted OAuth token storage
- Gmail sync authorization

These must be completed before exposing the corresponding production APIs.

## Next Phase

Phase 4 - Job Application REST APIs.
