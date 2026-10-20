import { useEffect, useState } from 'react'
import {
  getApplication,
  getApplicationEvents,
  type ApiApplication,
  type ApiTimelineEvent,
} from '../api/applications'
import { ApiError } from '../api/http'

interface Props {
  applicationId: string
  onBack: () => void
}

export default function LiveApplicationDetailPage({
  applicationId,
  onBack,
}: Props) {
  const [application, setApplication] = useState<ApiApplication | null>(null)
  const [events, setEvents] = useState<ApiTimelineEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let current = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const [record, timeline] = await Promise.all([
          getApplication(applicationId),
          getApplicationEvents(applicationId),
        ])
        if (current) {
          setApplication(record)
          setEvents(timeline.items)
        }
      } catch (cause) {
        if (current)
          setError(
            cause instanceof ApiError && cause.status === 404
              ? 'This application no longer exists.'
              : 'Application details could not be loaded.',
          )
      } finally {
        if (current) setLoading(false)
      }
    }
    void load()
    return () => {
      current = false
    }
  }, [applicationId])

  if (loading)
    return (
      <section className='detail-page live-page'>
        <button type='button' className='back-button' onClick={onBack}>
          Back to applications
        </button>
        <p role='status'>Loading application...</p>
      </section>
    )
  if (error || !application)
    return (
      <section className='detail-page live-page'>
        <button type='button' className='back-button' onClick={onBack}>
          Back to applications
        </button>
        <p role='alert'>{error ?? 'Application unavailable.'}</p>
      </section>
    )

  return (
    <section className='detail-page live-page'>
      <button type='button' className='back-button' onClick={onBack}>
        Back to applications
      </button>
      <div className='detail-heading'>
        <div>
          <p className='detail-eyebrow'>{application.current_stage}</p>
          <h2>{application.job_title}</h2>
          <p>
            {application.company_name}
            {application.location ? ` · ${application.location}` : ''}
          </p>
        </div>
        <span className='detail-owner'>{application.next_action_owner}</span>
      </div>
      <div className='detail-grid'>
        <article className='detail-card'>
          <h3>Application</h3>
          <dl>
            <dt>Source</dt>
            <dd>{application.application_source}</dd>
            <dt>Applied</dt>
            <dd>{application.applied_at ?? 'Not recorded'}</dd>
            <dt>Last activity</dt>
            <dd>{new Date(application.last_activity_at).toLocaleString()}</dd>
            <dt>Notes</dt>
            <dd>{application.notes ?? 'No notes'}</dd>
          </dl>
        </article>
        <article className='detail-card'>
          <h3>Timeline</h3>
          {events.length === 0 ? (
            <p>No timeline events recorded.</p>
          ) : (
            <ol className='live-timeline'>
              {events.map((event) => (
                <li key={event.id}>
                  <strong>{event.event_kind.replaceAll('_', ' ')}</strong>
                  <time dateTime={event.occurred_at}>
                    {new Date(event.occurred_at).toLocaleString()}
                  </time>
                  {event.details && <p>{JSON.stringify(event.details)}</p>}
                </li>
              ))}
            </ol>
          )}
        </article>
      </div>
    </section>
  )
}
