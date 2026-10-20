import type { UpcomingAction } from '../../types/dashboard'

interface Props {
  actions: UpcomingAction[]
  onViewApplication: (id: string) => void
}
const actionLabels = {
  ASSESSMENT: 'Assessment',
  INTERVIEW: 'Interview preparation',
  FOLLOW_UP: 'Follow-up',
}

export default function ActionQueue({ actions, onViewApplication }: Props) {
  return (
    <section className='timeline-overview-panel'>
      <div className='timeline-panel-heading'>
        <h3>Needs Your Attention</h3>
        <span>{actions.length} pending</span>
      </div>
      {actions.length === 0 ? (
        <p className='timeline-overview-empty'>No actions currently listed.</p>
      ) : (
        <ul className='attention-list'>
          {actions.map((action) => (
            <li key={action.id} className='attention-item'>
              <div className='attention-content'>
                <span className='attention-type'>
                  {actionLabels[action.type]}
                </span>
                <strong>{action.title}</strong>
                <p>{action.company}</p>
                <small>
                  {action.dueDate
                    ? `Due: ${action.dueDate}`
                    : 'Deadline not provided'}
                </small>
                <button
                  type='button'
                  className='text-button attention-link'
                  onClick={() => onViewApplication(action.applicationId)}
                >
                  View application
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
