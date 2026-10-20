import type { TrackedApplication } from '../../types/application'

interface Props {
  applications: TrackedApplication[]
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
const ownerLabels: Record<TrackedApplication['nextActionOwner'], string> = {
  USER: 'Your action',
  EMPLOYER: 'Employer',
  NONE: 'None',
}

export default function ApplicationTable({ applications }: Props) {
  if (applications.length === 0)
    return (
      <div className='applications-empty' role='status'>
        <h3>No matching applications</h3>
        <p>Try another search term or change the filters.</p>
      </div>
    )
  return (
    <div className='applications-table-scroll'>
      <table className='applications-table'>
        <thead>
          <tr>
            <th scope='col'>Company / Role</th>
            <th scope='col'>Location</th>
            <th scope='col'>Stage</th>
            <th scope='col'>Next Action</th>
            <th scope='col'>Last Activity</th>
          </tr>
        </thead>
        <tbody>
          {applications.map((application) => (
            <tr key={application.id}>
              <td>
                <div className='table-job-details'>
                  <strong>{application.jobTitle}</strong>
                  <span>{application.companyName}</span>
                </div>
              </td>
              <td>{application.location ?? 'Not specified'}</td>
              <td>
                <span
                  className={`stage-badge stage-${application.stage.toLowerCase()}`}
                >
                  {stageLabels[application.stage]}
                </span>
              </td>
              <td>{ownerLabels[application.nextActionOwner]}</td>
              <td>{application.lastActivityAt}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
