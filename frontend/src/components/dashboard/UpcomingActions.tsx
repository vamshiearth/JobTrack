import type { UpcomingAction } from '../../types/dashboard'

interface UpcomingActionsProps {
  actions: UpcomingAction[]
}

const icons = { ASSESSMENT: '📝', INTERVIEW: '📅', FOLLOW_UP: '✉️' }

export default function UpcomingActions({ actions }: UpcomingActionsProps) {
  return (
    <section className='dashboard-panel'>
      <div className='panel-heading'>
        <h3>Needs Your Attention</h3>
      </div>
      {actions.length === 0 ? (
        <p>No pending actions.</p>
      ) : (
        <div className='action-list'>
          {actions.map((action) => (
            <div key={action.id} className='action-row'>
              <span className='action-icon' aria-hidden='true'>
                {icons[action.type]}
              </span>
              <div className='action-details'>
                <strong>{action.title}</strong>
                <span>{action.company}</span>
                {action.dueDate && <small>Due: {action.dueDate}</small>}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
