# Phase 12: Job Source Integration

## Step 1: Greenhouse Read-Only Adapter

JobTrack's first discovery source is Greenhouse's public employer board API:

`GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true`

The adapter is read-only and does not create opportunities, applications, preparation packages, or submission events. It returns normalized `DiscoveredOpportunity` values for a later persistence and import step.

## Source Policy

- Board tokens are resolved through an explicit in-memory registry; arbitrary URLs and unknown tokens are rejected before any request.
- Requests use the fixed official `boards-api.greenhouse.io` HTTPS host.
- A five-second timeout and two-attempt limit bound network work. HTTP 429 responses receive one bounded retry.
- Malformed responses fail as a controlled `DiscoveryError`; no partial result is returned.
- Provider job IDs are stable source identifiers and duplicate IDs in one response are collapsed.
- Jobs missing an ID, title, or HTTPS URL are skipped.
- Returned descriptions are treated as untrusted HTML and reduced to plain text.
- Returned URLs must be HTTPS and cannot contain credentials. They are source links, not submission destinations.
- A failed refresh must not be interpreted as evidence that a previously observed listing was removed.

## Normalization Contract

Each accepted posting contains:

- `source`: `GREENHOUSE`
- `source_board`: validated employer board token
- `source_job_id`: provider job ID
- `company_name`: registry-controlled company name
- `job_title`
- optional `location`
- `source_url`
- optional sanitized `description`

Discovery remains separate from manually saved opportunities. Persistent catalog storage is added in migration `e1f2a3b4c5d6` through two tables:

- `discovery_sources` stores the validated provider and board token, enabled state, and the last successful refresh state.
- `discovered_jobs` stores normalized postings, provider IDs, SHA-256 content fingerprints, first/last seen timestamps, and `ACTIVE`, `NOT_SEEN`, or `UNKNOWN` availability.

The `(provider, board_token)` and `(source_id, provider_job_id)` constraints make refreshes idempotent. Ingestion locks the source row for the transaction, upserts jobs by provider ID, and reports created, updated, unchanged, and observed counts. Existing content is refreshed only after a successful fetch; adapter failures roll back the transaction and do not mark a source successful. Discovery never creates owner-scoped saved opportunities, applications, or `APPLICATION_SUBMITTED` events.

## Test Plan

Synthetic response tests cover valid normalization, duplicate IDs, missing fields, unsafe URLs, invalid board tokens, HTTP 429 retry, timeout failure, malformed JSON, and HTML description handling. No third-party network request is required for the test suite.

## Step 3: Discovery Search and Ranking

`GET /api/v1/discovery/jobs` filters the shared catalog by text, category, location, work arrangement, availability, and source, then applies pagination. `sort=match_score` evaluates the complete filtered set with the existing deterministic matcher before slicing the requested page. A missing candidate profile is reported as `NEEDS_PROFILE`; insufficient job evidence and eligibility language retain the matcher’s explicit statuses. Manual saved state is calculated only against the authenticated user’s opportunities.

Work arrangement is stored as `REMOTE`, `HYBRID`, `ONSITE`, or `UNKNOWN`, with separate location restriction text when the feed provides evidence. The metadata migration is `f2a3b4c5d6e7`.

## Boundaries

This step does not automate applications, infer work authorization, or submit employer forms. Greenhouse, Lever, and Ashby remain employer-specific feeds; future integrations require their own validated source policy. Persistence tests run against the isolated `jobtrack_step5_test` database; the development database is not modified.
