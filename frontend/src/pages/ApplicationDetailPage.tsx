import ApplicationTimeline from '../components/timeline/ApplicationTimeline'
import { mockTimeline } from '../data/mockTimeline'
import type { TrackedApplication } from '../types/application'

interface Props {
  application: TrackedApplication
  onBack: () => void
}

const stageLabels: Record<TrackedApplication['stage'], string> = {
  APPLIED: 'Applied',
  SCREENING: 'Screening',
  ASSESSMENT: 'Assessment',
  INTERVIEW: 'Interview',
  OFFER: 'Offer',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
}
const nextActionLabels = {
  USER: 'Your action required',
  EMPLOYER: 'Waiting for employer',
  NONE: 'No pending action',
}

export default function ApplicationDetailPage({ application, onBack }: Props) {
  const events = mockTimeline.filter(
    (event) => event.applicationId === application.id,
  )

  return (
    <section className='application-detail-page'>
      <button type='button' className='detail-back-button' onClick={onBack}>
        ← Back to applications
      </button>
      <div className='detail-intro'>
        <div>
          <h2>{application.jobTitle}</h2>
          <p>
            {application.companyName}
            {application.location ? ` · ${application.location}` : ''}
          </p>
        </div>
        <span className='demo-label'>Demo data</span>
      </div>
      <div className='detail-status-row'>
        <span
          className={`stage-badge stage-${application.stage.toLowerCase()}`}
        >
          {stageLabels[application.stage]}
        </span>
        <span className='detail-action-owner'>
          {nextActionLabels[application.nextActionOwner]}
        </span>
      </div>
      <div className='detail-grid'>
        <section className='detail-panel'>
          <h3>Application information</h3>
          <dl className='application-facts'>
            <div>
              <dt>Company</dt>
              <dd>{application.companyName}</dd>
            </div>
            <div>
              <dt>Position</dt>
              <dd>{application.jobTitle}</dd>
            </div>
            <div>
              <dt>Location</dt>
              <dd>{application.location ?? 'Not provided'}</dd>
            </div>
            <div>
              <dt>Applied</dt>
              <dd>{application.appliedAt}</dd>
            </div>
            <div>
              <dt>Last activity</dt>
              <dd>{application.lastActivityAt}</dd>
            </div>
          </dl>
        </section>
        <section className='detail-panel'>
          <h3>Recruitment timeline</h3>
          <ApplicationTimeline events={events} />
        </section>
      </div>
    </section>
  )
}
