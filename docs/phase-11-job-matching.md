# JobTrack Phase 11: Explainable Job Matching

The first matching model is deterministic and ranks opportunities, not hiring probability.

## Evidence and Preferences

Candidate skills and experience are explicitly confirmed profile values. Target roles, locations, and remote preference affect ranking only; they are not qualifications. The matcher never infers work authorization, sponsorship, clearance, or other eligibility facts. Those terms produce `NEEDS_REVIEW`.

## Scoring

When a description contains recognized requirements, the score is the rounded sum of:

- Technical skill evidence: 40 points, proportional to confirmed skills among recognized requirements.
- Role relevance: 25 points when the title contains a confirmed target role.
- Experience relevance: 20 points when the confirmed experience summary supports a matched skill.
- Location/work preference: 15 points when location or work arrangement matches a stated preference.

Missing descriptions or recognized requirements produce `score: null` and `INSUFFICIENT_EVIDENCE`.

## Supported Aliases

`java`, `spring_boot` (`spring boot`, `springboot`), `python`, `fastapi`, `react`, `typescript`, `postgresql` (`postgres`, `postgres db`), `oracle_cpq` (`oracle cpq`, `oracle cpq cloud`), `sql`, and `docker`.

Matching uses phrase boundaries and does not count unknown aliases. Unverified recognized requirements are reported separately from matched evidence.

## Freshness

Assessments store the profile revision, opportunity update timestamp, and scoring model version. A profile or opportunity change makes the current assessment unavailable until refreshed. Matching creates no application or application-event records.
