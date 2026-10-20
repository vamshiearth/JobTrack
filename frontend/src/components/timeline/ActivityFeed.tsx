import type { ActivityItem } from '../../utils/timelineFeed'
import { eventLabels } from '../../utils/timelineFeed'

interface Props {
  items: ActivityItem[]
  onViewApplication: (id: string) => void
}

export default function ActivityFeed({ items, onViewApplication }: Props) {
  if (items.length === 0)
    return (
      <div className='timeline-overview-empty' role='status'>
        <h3>No matching activity</h3>
        <p>Try a different search or event category.</p>
      </div>
    )
  return (
    <ol className='activity-feed'>
      {items.map(({ event, application }) => (
        <li key={event.id} className='activity-feed-item'>
          <span className='activity-feed-marker' aria-hidden='true' />
          <div className='activity-feed-body'>
            <div className='activity-feed-heading'>
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
            </div>
            <p>
              {application.companyName} · {application.jobTitle}
            </p>
            {event.note && <p className='activity-event-note'>{event.note}</p>}
            <button
              type='button'
              className='text-button activity-view-link'
              onClick={() => onViewApplication(application.id)}
            >
              View application
            </button>
          </div>
        </li>
      ))}
    </ol>
  )
}
