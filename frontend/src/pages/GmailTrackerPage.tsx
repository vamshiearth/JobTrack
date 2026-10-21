import { useCallback, useEffect, useState } from 'react'
import { getApplications, type ApiApplication } from '../api/applications'
import { refreshGmailTracker } from '../api/gmail'

interface Props {
  csrfToken: string
}

const applicationQuery = {
  q: '',
  stage: 'ALL' as const,
  nextActionOwner: 'ALL' as const,
  page: 1,
  pageSize: 100,
  sortBy: 'last_activity_at' as const,
  sortOrder: 'desc' as const,
}

function countStage(applications: ApiApplication[], stage: string) {
  return applications.filter(
    (application) => application.current_stage === stage,
  ).length
}

export default function GmailTrackerPage({ csrfToken }: Props) {
  const [applications, setApplications] = useState<ApiApplication[] | null>(
    null,
  )
  const [refreshing, setRefreshing] = useState(false)
  const [status, setStatus] = useState('Loading tracked applications...')

  const loadApplications = useCallback(async () => {
    const result = await getApplications(applicationQuery)
    setApplications(result.items)
  }, [])

  useEffect(() => {
    queueMicrotask(() => void loadApplications().catch(() => undefined))
  }, [loadApplications])

  async function refreshGmail() {
    setRefreshing(true)
    setStatus('Checking Gmail for application updates...')
    try {
      const result = await refreshGmailTracker(csrfToken)
      await loadApplications()
      setStatus(
        `Refresh complete: ${result.applications_added} added, ${result.status_changes} status updates, ${result.needs_review} needs review`,
      )
    } catch {
      setStatus('Unable to refresh Gmail. Existing applications were kept.')
    } finally {
      setRefreshing(false)
    }
  }

  const trackedApplications = applications ?? []
  const interviews = countStage(trackedApplications, 'INTERVIEW')
  const assessments = countStage(trackedApplications, 'ASSESSMENT')

  return (
    <section className='tracker-page live-page'>
      <div className='tracker-intro'>
        <div>
          <p className='detail-eyebrow'>GMAIL TRACKER</p>
          <h2>Track applications from your inbox.</h2>
          <p>Check Gmail and keep your application pipeline current.</p>
        </div>
        <button
          type='button'
          className='primary-action'
          onClick={() => void refreshGmail()}
          disabled={refreshing || !csrfToken}
        >
          {refreshing ? 'Checking Gmail...' : 'Refresh Gmail'}
        </button>
      </div>

      <p className='tracker-status' role='status'>
        {status}
      </p>

      <div className='tracker-stats' aria-label='Application summary'>
        <div>
          <span>Applications</span>
          <strong>{trackedApplications.length}</strong>
        </div>
        <div>
          <span>Interviews</span>
          <strong>{interviews}</strong>
        </div>
        <div>
          <span>Assessments</span>
          <strong>{assessments}</strong>
        </div>
      </div>

      {applications === null ? (
        <p role='status'>Loading applications...</p>
      ) : trackedApplications.length === 0 ? (
        <div className='applications-empty' role='status'>
          <h3>No tracked applications yet</h3>
          <p>Refresh Gmail to look for application activity.</p>
        </div>
      ) : (
        <div className='applications-table-scroll'>
          <table className='applications-table'>
            <thead>
              <tr>
                <th scope='col'>Company / Role</th>
                <th scope='col'>Status</th>
                <th scope='col'>Last activity</th>
              </tr>
            </thead>
            <tbody>
              {trackedApplications.map((application) => (
                <tr key={application.id}>
                  <td>
                    <div className='table-job-details'>
                      <strong>{application.job_title}</strong>
                      <span>{application.company_name}</span>
                    </div>
                  </td>
                  <td>{application.current_stage}</td>
                  <td>
                    {new Date(application.last_activity_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
