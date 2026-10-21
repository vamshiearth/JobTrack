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

Discovery remains separate from manually saved opportunities until a later step defines persistence, deduplication across refreshes, freshness state, filtering, and an explicit user import action.

## Test Plan

Synthetic response tests cover valid normalization, duplicate IDs, missing fields, unsafe URLs, invalid board tokens, HTTP 429 retry, timeout failure, malformed JSON, and HTML description handling. No third-party network request is required for the test suite.

## Boundaries

This step does not automate applications, infer work authorization, submit employer forms, or add a database migration. Greenhouse, Lever, and Ashby remain employer-specific feeds; future integrations require their own validated source policy.
