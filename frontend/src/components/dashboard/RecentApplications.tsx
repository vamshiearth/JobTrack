import type { ApplicationStage, RecentApplication } from '../../types/dashboard'

interface RecentApplicationsProps {
  applications: RecentApplication[]
  onViewAll: () => void
}

const stageLabels: Record<ApplicationStage, string> = {
  APPLIED: 'Applied',
  SCREENING: 'Screening',
  ASSESSMENT: 'Assessment',
  INTERVIEW: 'Interview',
  OFFER: 'Offer',
  REJECTED: 'Rejected',
  WITHDRAWN: 'Withdrawn',
}

export default function RecentApplications({
  applications,
  onViewAll,
}: RecentApplicationsProps) {
  return (
    <section className='dashboard-panel'>
      <div className='panel-heading'>
        <h3>Recent Applications</h3>
        <button type='button' className='text-button' onClick={onViewAll}>
          View all
        </button>
      </div>
      {applications.length === 0 ? (
        <p>No applications to display.</p>
      ) : (
        <div className='application-list'>
          {applications.map((application) => (
            <div key={application.id} className='application-row'>
              <div className='company-avatar'>
                {application.company.charAt(0)}
              </div>
              <div className='application-details'>
                <strong>{application.jobTitle}</strong>
                <span>
                  {application.company} · {application.lastActivity}
                </span>
              </div>
              <span
                className={`stage-badge stage-${application.stage.toLowerCase()}`}
              >
                {stageLabels[application.stage]}
              </span>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
