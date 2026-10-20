import { useEffect, useState } from 'react'
import { loadDashboard, type LiveDashboardData } from '../api/dashboard'

interface Props {
  onViewApplication: (id: string) => void
  onViewApplications: () => void
}

export default function LiveDashboardPage({
  onViewApplication,
  onViewApplications,
}: Props) {
  const [data, setData] = useState<LiveDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [reloadVersion, setReloadVersion] = useState(0)

  useEffect(() => {
    let active = true
    async function load() {
      try {
        const result = await loadDashboard()
        if (!active) return
        setData(result)
        setError(null)
      } catch {
        if (!active) return
        setData(null)
        setError('Dashboard information could not be loaded.')
      } finally {
        if (active) setLoading(false)
      }
    }
    void load()
    return () => {
      active = false
    }
  }, [reloadVersion])

  if (loading) return <p role='status'>Loading dashboard...</p>
  if (error || !data) {
    return (
      <section className='live-dashboard-page'>
        <h2>Dashboard</h2>
        <p role='alert'>{error ?? 'Dashboard information is unavailable.'}</p>
        <button type='button' onClick={() => setReloadVersion((value) => value + 1)}>
          Retry
        </button>
      </section>
    )
  }

  const cards = [
    ['Total applications', data.totalApplications],
    ['Interviews', data.interviewCount],
    ['Assessments', data.assessmentCount],
    ['Offers', data.offerCount],
  ] as const

  return (
    <section className='live-dashboard-page'>
      <div className='live-page-heading'>
        <div><h2>My Dashboard</h2><p>Your saved JobTrack applications.</p></div>
        <button type='button' className='dashboard-refresh' onClick={() => setReloadVersion((value) => value + 1)}>Refresh</button>
      </div>
      <div className='live-stats-grid'>
        {cards.map(([label, value]) => <div key={label} className='live-stat-card'><span>{label}</span><strong>{value}</strong></div>)}
      </div>
      <div className='live-dashboard-columns'>
        <section className='live-data-panel'>
          <div className='live-panel-heading'><h3>Recent Applications</h3><button type='button' onClick={onViewApplications}>View all</button></div>
          {data.recentApplications.length === 0 ? <p className='live-empty-message'>No applications saved yet.</p> : <ul className='live-record-list'>{data.recentApplications.map((app) => <li key={app.id}><div><strong>{app.job_title}</strong><span>{app.company_name}</span><small>Stage: {app.current_stage}</small></div><button type='button' onClick={() => onViewApplication(app.id)}>View</button></li>)}</ul>}
        </section>
        <section className='live-data-panel'>
          <div className='live-panel-heading'><h3>Needs Your Attention</h3><span>{data.totalUserActions} total</span></div>
          {data.userActions.length === 0 ? <p className='live-empty-message'>No applications currently require your next action.</p> : <ul className='live-record-list'>{data.userActions.map((app) => <li key={app.id}><div><strong>{app.job_title}</strong><span>{app.company_name}</span><small>Current stage: {app.current_stage}</small></div><button type='button' onClick={() => onViewApplication(app.id)}>Open</button></li>)}</ul>}
          {data.totalUserActions > data.userActions.length && <p className='live-panel-note'>Showing the 10 most recently active applications requiring action.</p>}
        </section>
      </div>
    </section>
  )
}