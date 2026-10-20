import type { TimelineEvent } from '../types/timeline'

export const mockTimeline: TimelineEvent[] = [
  {
    id: 'event-1',
    applicationId: 'demo-1',
    kind: 'APPLICATION_SUBMITTED',
    occurredAt: '2026-10-10T14:00:00Z',
    interviewRound: null,
    note: null,
  },
  {
    id: 'event-2',
    applicationId: 'demo-1',
    kind: 'RECRUITER_CONTACTED',
    occurredAt: '2026-10-15T14:00:00Z',
    interviewRound: null,
    note: 'Recruiter requested additional information.',
  },
  {
    id: 'event-3',
    applicationId: 'demo-1',
    kind: 'ASSESSMENT_INVITED',
    occurredAt: '2026-10-19T14:00:00Z',
    interviewRound: null,
    note: 'Assessment invitation received.',
  },
  {
    id: 'event-4',
    applicationId: 'demo-3',
    kind: 'APPLICATION_SUBMITTED',
    occurredAt: '2026-10-08T14:00:00Z',
    interviewRound: null,
    note: null,
  },
  {
    id: 'event-5',
    applicationId: 'demo-3',
    kind: 'INTERVIEW_SCHEDULED',
    occurredAt: '2026-10-17T14:00:00Z',
    interviewRound: 1,
    note: 'First interview scheduled.',
  },
]
