# JobTrack - Phase 6 Authentication Design

## Goal

Replace deny-by-default placeholder authentication with verified Google identity
and secure server sessions.

## Authentication Flow

1. Browser initiates Google sign-in through FastAPI.
2. FastAPI creates and stores a short-lived OAuth transaction containing state,
   nonce and PKCE data.
3. Google authenticates the user and redirects to FastAPI.
4. Backend validates state and exchanges the code.
5. Backend verifies Google's ID token, including signature, issuer, audience,
   expiry and nonce.
6. Backend resolves the user using Google's stable `sub` identifier.
7. Backend creates a server-side session.
8. Browser receives an HttpOnly session cookie.
9. Protected API dependencies validate the session.
10. Logout revokes the session.

## Session Security

- Store only session-token hashes in PostgreSQL.
- Generate tokens using cryptographic randomness.
- Use HttpOnly, Secure-in-production cookies.
- Use explicit cookie SameSite and path policies.
- Set finite session expiration.
- Revoke sessions on logout.
- Protect authenticated write endpoints against CSRF.
- Restrict CORS to configured trusted origins.
- Do not store session credentials in localStorage.
- Never log OAuth codes, cookies or secrets.

## Database Requirements

- Extend users with stable Google identity support.
- Create an authentication sessions table.
- Add indexes and constraints.
- Apply all changes through Alembic migrations.

## Separation of Permissions

Google sign-in requests only identity scopes: `openid`, `email` and `profile`.

Gmail authorization is a separate future feature.

## Planned Authentication Endpoints

| Method | Endpoint                       | Purpose                                    |
| ------ | ------------------------------ | ------------------------------------------ |
| GET    | `/api/v1/auth/google/login`    | Start Google sign-in                       |
| GET    | `/api/v1/auth/google/callback` | Validate OAuth response and create session |
| GET    | `/api/v1/auth/me`              | Return authenticated user information      |
| POST   | `/api/v1/auth/logout`          | Revoke current session                     |

The existing `get_current_user_id()` dependency must continue returning `401`
until authenticated database-session resolution is fully implemented and tested.

## Required Tests

- Invalid or missing OAuth state rejected.
- Invalid ID tokens rejected.
- Unknown or expired sessions rejected.
- Session revocation enforced.
- Cross-user ownership preserved.
- CSRF validation enforced for writes.
- Authentication failures do not expose secrets.
- Existing APIs remain protected during migration.

## Release Dependencies

- Phase 5 manual browser and viewport walkthrough.
- Google OAuth application configuration.
- HTTPS deployment and cookie policy review.
- Security and integration regression testing.

## Implementation Boundary

This step documents architecture only. It does not add an authentication bypass,
database migration, Google credentials, or OAuth callback code.
