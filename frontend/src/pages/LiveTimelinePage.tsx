import { useEffect, useMemo, useState } from 'react'
import { loadTimeline, type LiveTimelineData } from '../api/dashboard'
import { eventLabels, type EventCategory } from '../utils/timelineFeed'
import type { TimelineEventKind } from '../types/timeline'

interface Props { onViewApplication: (id: string) => void }

function eventCategory(kind: TimelineEventKind): Exclude<EventCategory, 'ALL'> {
  if (kind.startsWith('ASSESSMENT_')) return 'ASSESSMENT'
  if (kind.startsWith('INTERVIEW_')) return 'INTERVIEW'
  if (kind === 'OFFER_RECEIVED' || kind === 'REJECTION_RECEIVED' || kind === 'APPLICATION_WITHDRAWN') return 'OUTCOME'
  return 'APPLICATION'
}

export default function LiveTimelinePage({ onViewApplication }: Props) {
  const [data, setData] = useState<LiveTimelineData | null>(null)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<EventCategory>('ALL')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadVersion, setReloadVersion] = useState(0)

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await loadTimeline()
        if (!active) return
        setData(result)
        setError(null)
      } catch {
        if (!active) return
        setData(null)
        setError('Recruitment activity could not be loaded.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => { active = false }
  }, [reloadVersion])

  const activities = useMemo(() => {
    if (!data) return []
    const search = query.trim().toLowerCase()
    return data.activities.filter(({ application, event }) => {
      const content = [application.company_name, application.job_title, eventLabels[event.event_kind]].join(' ').toLowerCase()
      return (!search || content.includes(search)) && (category === 'ALL' || eventCategory(event.event_kind) === category)
    })
  }, [data, query, category])

  if (loading) return <p role='status'>Loading recruitment activity...</p>
  if (error || !data) {
    return <section className='live-timeline-page'><h2>Recruitment Timeline</h2><p role='alert'>{error ?? 'Activity is unavailable.'}</p><button type='button' onClick={() => setReloadVersion((value) => value + 1)}>Retry</button></section>
  }

  return (
    <section className='live-timeline-page'>
      <div className='live-page-heading'><div><h2>Recruitment Timeline</h2><p>Recent recruitment activity from your saved applications.</p></div><button type='button' className='dashboard-refresh' onClick={() => setReloadVersion((value) => value + 1)}>Refresh</button></div>
      <p className='timeline-scope-note'>Showing events from the {data.sampledApplications} most recently active applications{data.totalApplications > data.sampledApplications ? ` out of ${data.totalApplications} total.` : '.'}</p>
      <div className='live-data-panel'>
        <div className='timeline-filter-bar'>
          <label>Search activity<input type='search' value={query} placeholder='Company, role or event' onChange={(event) => setQuery(event.target.value)} /></label>
          <label>Event category<select value={category} onChange={(event) => setCategory(event.target.value as EventCategory)}><option value='ALL'>All events</option><option value='APPLICATION'>Applications / Recruiters</option><option value='ASSESSMENT'>Assessments</option><option value='INTERVIEW'>Interviews</option><option value='OUTCOME'>Offers / Outcomes</option></select></label>
        </div>
        {activities.length === 0 ? <div className='live-empty-message' role='status'>{data.activities.length === 0 ? 'No recruitment events found in the recent application sample.' : 'No events match these filters in the recent application sample.'}</div> : <ol className='activity-feed'>{activities.map(({ application, event }) => <li key={`${application.id}-${event.id}`} className='activity-feed-item'><span className='activity-feed-marker' aria-hidden='true' /><div className='activity-feed-body'><div className='activity-feed-heading'><strong>{eventLabels[event.event_kind]}{event.interview_round !== null ? ` — Round ${event.interview_round}` : ''}</strong><time dateTime={event.occurred_at}>{new Date(event.occurred_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</time></div><p>{application.company_name} · {application.job_title}</p><button type='button' className='view-details-button' onClick={() => onViewApplication(application.id)}>View application</button></div></li>)}</ol>}
      </div>
    </section>
  )
}