import { useMemo, useState } from 'react'
import ActivityFeed from '../components/timeline/ActivityFeed'
import ActionQueue from '../components/timeline/ActionQueue'
import { mockApplications } from '../data/mockApplications'
import { mockTimeline } from '../data/mockTimeline'
import { mockUpcomingActions } from '../data/mockDashboard'
import { buildTimelineFeed, type EventCategory } from '../utils/timelineFeed'

interface TimelinePageProps {
  onViewApplication: (id: string) => void
}

export default function TimelinePage({ onViewApplication }: TimelinePageProps) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<EventCategory>('ALL')
  const activities = useMemo(
    () => buildTimelineFeed(mockApplications, mockTimeline, query, category),
    [query, category],
  )

  return (
    <section className='timeline-overview-page'>
      <div className='timeline-overview-intro'>
        <div>
          <h2>Recruitment Timeline</h2>
          <p>Review recruitment activity across your applications.</p>
        </div>
        <span className='demo-label'>Demo data - not synced with Gmail</span>
      </div>
      <div className='timeline-summary-grid'>
        <div className='timeline-summary-card'>
          <span>Timeline events</span>
          <strong>{mockTimeline.length}</strong>
        </div>
        <div className='timeline-summary-card'>
          <span>Actions requiring attention</span>
          <strong>{mockUpcomingActions.length}</strong>
        </div>
      </div>
      <div className='timeline-overview-grid'>
        <section className='timeline-overview-panel'>
          <div className='timeline-panel-heading'>
            <h3>Activity Feed</h3>
            <span>{activities.length} matching</span>
          </div>
          <div className='timeline-filter-bar'>
            <label>
              Search activity
              <input
                type='search'
                placeholder='Company, role, or event'
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
            </label>
            <label>
              Event category
              <select
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value as EventCategory)
                }
              >
                <option value='ALL'>All events</option>
                <option value='APPLICATION'>Application / Recruiter</option>
                <option value='ASSESSMENT'>Assessments</option>
                <option value='INTERVIEW'>Interviews</option>
                <option value='OUTCOME'>Offers / Outcomes</option>
              </select>
            </label>
          </div>
          <ActivityFeed
            items={activities}
            onViewApplication={onViewApplication}
          />
        </section>
        <ActionQueue
          actions={mockUpcomingActions}
          onViewApplication={onViewApplication}
        />
      </div>
    </section>
  )
}
