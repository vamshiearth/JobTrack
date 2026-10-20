import type { TrackedApplication } from '../types/application'
import type { TimelineEvent, TimelineEventKind } from '../types/timeline'

export type EventCategory =
  | 'ALL'
  | 'APPLICATION'
  | 'ASSESSMENT'
  | 'INTERVIEW'
  | 'OUTCOME'

export interface ActivityItem {
  event: TimelineEvent
  application: TrackedApplication
}

export const eventLabels: Record<TimelineEventKind, string> = {
  APPLICATION_SUBMITTED: 'Application submitted',
  RECRUITER_CONTACTED: 'Recruiter contacted',
  ASSESSMENT_INVITED: 'Assessment invited',
  ASSESSMENT_COMPLETED: 'Assessment completed',
  INTERVIEW_SCHEDULED: 'Interview scheduled',
  INTERVIEW_COMPLETED: 'Interview completed',
  OFFER_RECEIVED: 'Offer received',
  REJECTION_RECEIVED: 'Rejection received',
  APPLICATION_WITHDRAWN: 'Application withdrawn',
}

function categoryFor(kind: TimelineEventKind): Exclude<EventCategory, 'ALL'> {
  if (kind.startsWith('ASSESSMENT_')) return 'ASSESSMENT'
  if (kind.startsWith('INTERVIEW_')) return 'INTERVIEW'
  if (
    kind === 'OFFER_RECEIVED' ||
    kind === 'REJECTION_RECEIVED' ||
    kind === 'APPLICATION_WITHDRAWN'
  )
    return 'OUTCOME'
  return 'APPLICATION'
}

export function buildTimelineFeed(
  applications: TrackedApplication[],
  events: TimelineEvent[],
  query = '',
  category: EventCategory = 'ALL',
): ActivityItem[] {
  const applicationsById = new Map(
    applications.map((application) => [application.id, application]),
  )
  const normalizedQuery = query.trim().toLowerCase()
  return events
    .flatMap((event): ActivityItem[] => {
      const application = applicationsById.get(event.applicationId)
      return application ? [{ event, application }] : []
    })
    .filter(({ event, application }) => {
      const text = [
        application.companyName,
        application.jobTitle,
        eventLabels[event.kind],
      ]
        .join(' ')
        .toLowerCase()
      return (
        (!normalizedQuery || text.includes(normalizedQuery)) &&
        (category === 'ALL' || categoryFor(event.kind) === category)
      )
    })
    .sort(
      (a, b) =>
        b.event.occurredAt.localeCompare(a.event.occurredAt) ||
        a.event.id.localeCompare(b.event.id),
    )
}
