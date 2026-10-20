import type { TimelineEvent, TimelineEventKind } from '../../types/timeline'

interface Props {
  events: TimelineEvent[]
}

const eventLabels: Record<TimelineEventKind, string> = {
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

export default function ApplicationTimeline({ events }: Props) {
  const sortedEvents = [...events].sort(
    (a, b) =>
      a.occurredAt.localeCompare(b.occurredAt) || a.id.localeCompare(b.id),
  )

  if (sortedEvents.length === 0) {
    return (
      <p className='timeline-empty'>
        No timeline events are available in this demo.
      </p>
    )
  }

  return (
    <ol className='recruitment-timeline'>
      {sortedEvents.map((event) => (
        <li key={event.id} className='timeline-entry'>
          <span className='timeline-marker' aria-hidden='true' />
          <div className='timeline-entry-content'>
            <strong>
              {eventLabels[event.kind]}
              {event.interviewRound !== null
                ? ` - Round ${event.interviewRound}`
                : ''}
            </strong>
            <time dateTime={event.occurredAt}>
              {new Date(event.occurredAt).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                timeZone: 'UTC',
              })}
            </time>
            {event.note && <p>{event.note}</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}
