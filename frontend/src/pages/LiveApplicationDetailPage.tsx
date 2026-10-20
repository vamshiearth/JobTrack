import { useEffect, useState } from 'react'
import {
  getApplication,
  getApplicationEvents,
  type ApiApplication,
  type ApiTimelineEvent,
} from '../api/applications'
import { ApiError } from '../api/http'
import EditApplicationForm from '../components/applications/EditApplicationForm'
import DeleteApplicationConfirm from '../components/applications/DeleteApplicationConfirm'
import UpdateProgressForm from '../components/applications/UpdateProgressForm'

interface Props {
  applicationId: string
  csrfToken: string
  onBack: () => void
  onDeleted: () => void
}

export default function LiveApplicationDetailPage({
  applicationId,
  csrfToken,
  onBack,
  onDeleted,
}: Props) {
  const [application, setApplication] = useState<ApiApplication | null>(null)
  const [events, setEvents] = useState<ApiTimelineEvent[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [updatingProgress, setUpdatingProgress] = useState(false)
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [reloadVersion, setReloadVersion] = useState(0)

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
  }, [applicationId, reloadVersion])

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
      {confirmingDelete ? (
        <DeleteApplicationConfirm
          application={application}
          csrfToken={csrfToken}
          onCancel={() => setConfirmingDelete(false)}
          onDeleted={onDeleted}
        />
      ) : editing ? (
        <div className='detail-panel'>
          <h2>Edit Application</h2>
          <EditApplicationForm
            key={application.id}
            application={application}
            csrfToken={csrfToken}
            onCancel={() => setEditing(false)}
            onSaved={() => {
              setEditing(false)
              setReloadVersion((value) => value + 1)
            }}
          />
        </div>
      ) : updatingProgress ? (
        <section className='detail-panel'>
          <h2>Update Recruitment Progress</h2>
          <UpdateProgressForm
            applicationId={application.id}
            csrfToken={csrfToken}
            onCancel={() => setUpdatingProgress(false)}
            onSaved={() => {
              setUpdatingProgress(false)
              setReloadVersion((value) => value + 1)
            }}
          />
        </section>
      ) : (
        <>
          <div className='detail-heading detail-intro'>
            <div>
              <p className='detail-eyebrow'>{application.current_stage}</p>
              <h2>{application.job_title}</h2>
              <p>
                {application.company_name}
                {application.location ? ` · ${application.location}` : ''}
              </p>
            </div>
            <span className='detail-owner'>
              {application.next_action_owner}
            </span>
            <div className='detail-actions'>
              <button
                type='button'
                className='primary-action'
                onClick={() => {
                  setEditing(false)
                  setUpdatingProgress(true)
                }}
              >
                Update Progress
              </button>
              <button
                type='button'
                onClick={() => {
                  setUpdatingProgress(false)
                  setEditing(true)
                }}
              >
                Edit Application
              </button>
              <button
                type='button'
                className='delete-trigger'
                onClick={() => {
                  setEditing(false)
                  setUpdatingProgress(false)
                  setConfirmingDelete(true)
                }}
              >
                Delete Application
              </button>
            </div>
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
                <dd>
                  {new Date(application.last_activity_at).toLocaleString()}
                </dd>
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
        </>
      )}
    </section>
  )
}
