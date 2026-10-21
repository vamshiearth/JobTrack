# JobTrack - Phase 10 Classification Audit

## Baseline

- Gmail metadata records: 104
- Initial review suggestions: 14
- Pending after live rejection test: 13
- Current classifier category: RECRUITER_CONTACTED
- Existing applications: 0
- Current live page observation: 10 pending review cards were visible during this audit; this differs from the previously recorded count of 13 and was not changed during the audit.

## Manual Evaluation

| Category                   | Count |
| -------------------------- | ----: |
| Genuine recruiter contact  |     1 |
| Application acknowledgment |     5 |
| Interview or assessment    |     0 |
| Unrelated / promotional    |     3 |
| Unclear                    |     1 |

## Evidence Summary

- The single likely recruiter-contact message used direct follow-up language asking whether the recipient was still interested in jobs.
- Five messages were recognizable as application-platform acknowledgments, including application completion and thank-you confirmations.
- No visible item provided sufficient evidence of an interview or assessment event.
- Three messages were platform or job-alert activity: an account-permission notice and generic opportunity recommendations.
- One recruiting-platform one-time-passcode message was insufficient to associate with a recruitment event.
- Sender and subject evidence was sufficient to identify a recruiting platform for most items, but not to establish an owned employer application because there were no existing applications.

## Findings

- Repeated false-positive patterns: all observed items were classified as `RECRUITER_CONTACTED`, including automated acknowledgments, platform notices, job alerts, and a one-time passcode.
- Ambiguous sender patterns: recruiting platforms and notification mailboxes were treated as recruiter evidence even when the subject indicated automation.
- Employer-matching limitations: platform senders exposed the recruiting intermediary but did not reliably identify an owned employer/application.
- Missing classification rules: application acknowledgment, job alert, account-permission, and one-time-passcode signals need precedence over generic recruiter-language matching.

## Read-Only Classifier Evaluation

| Measure                            |                               Result |
| ---------------------------------- | -----------------------------------: |
| Evaluated messages                 |                                   10 |
| Correct category assignments       |                                   10 |
| Incorrect assignments              |                                    0 |
| Uncertain/unknown assignments      |                                    4 |
| Remaining unreviewed pending cards | 3, subject to current database count |

The comparison used synthetic subjects representing the labeled audit sample and called the pure classifier directly. It did not call the classification endpoint or change review decisions.

## Safety Requirements

- Never auto-approve recruitment events.
- Never modify applications from classification alone.
- Do not infer interview completion from a subject.
- Maintain same-user ownership and review deduplication.
- Do not collect Gmail message bodies.

## Next Action

Use the audit results to improve deterministic
classification rules and add regression tests.
