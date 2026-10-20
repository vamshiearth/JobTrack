import { useMemo, useState } from 'react'
import ApplicationFilters from '../components/applications/ApplicationFilters'
import ApplicationPagination from '../components/applications/ApplicationPagination'
import ApplicationTable from '../components/applications/ApplicationTable'
import { mockApplications } from '../data/mockApplications'
import type { ApplicationFilters as Filters } from '../types/application'
import { filterApplications } from '../utils/applicationFilters'

const initialFilters: Filters = {
  q: '', stage: 'ALL', nextActionOwner: 'ALL', sortBy: 'last_activity_at', sortOrder: 'desc', page: 1, pageSize: 4,
}

export default function ApplicationsPage() {
  const [filters, setFilters] = useState<Filters>(initialFilters)
  const result = useMemo(() => filterApplications(mockApplications, filters), [filters])

  return (
    <section className='applications-page'>
      <div className='applications-intro'><div><h2>My Applications</h2><p>Browse your applications and recruitment progress in one place.</p></div><span className='demo-label'>Demo data - not synced with Gmail</span></div>
      <div className='applications-panel'>
        <ApplicationFilters filters={filters} onChange={setFilters} />
        <div className='applications-results-heading'><strong>Applications</strong><span>{result.total} matching</span></div>
        <ApplicationTable applications={result.items} />
        <ApplicationPagination page={result.page} totalPages={result.totalPages} total={result.total} pageSize={result.pageSize} onPageChange={(page) => setFilters((current) => ({ ...current, page }))} />
      </div>
    </section>
  )
}
