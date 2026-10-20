import type { ActionOwner, ApplicationStage } from '../../types/dashboard'
import type {
  ApplicationFilters as Filters,
  ApplicationSort,
  SortOrder,
} from '../../types/application'

interface Props {
  filters: Filters
  onChange: (filters: Filters) => void
}

export default function ApplicationFilters({ filters, onChange }: Props) {
  function update(changes: Partial<Filters>) {
    onChange({ ...filters, ...changes, page: 1 })
  }

  return (
    <div className='applications-toolbar'>
      <label className='filter-field search-field'>
        <span>Search applications</span>
        <input
          type='search'
          placeholder='Company or job title'
          value={filters.q}
          onChange={(event) => update({ q: event.target.value })}
        />
      </label>
      <label className='filter-field'>
        <span>Stage</span>
        <select
          value={filters.stage}
          onChange={(event) =>
            update({ stage: event.target.value as ApplicationStage | 'ALL' })
          }
        >
          <option value='ALL'>All stages</option>
          <option value='APPLIED'>Applied</option>
          <option value='SCREENING'>Screening</option>
          <option value='ASSESSMENT'>Assessment</option>
          <option value='INTERVIEW'>Interview</option>
          <option value='OFFER'>Offer</option>
          <option value='REJECTED'>Rejected</option>
          <option value='WITHDRAWN'>Withdrawn</option>
        </select>
      </label>
      <label className='filter-field'>
        <span>Next action</span>
        <select
          value={filters.nextActionOwner}
          onChange={(event) =>
            update({
              nextActionOwner: event.target.value as ActionOwner | 'ALL',
            })
          }
        >
          <option value='ALL'>All</option>
          <option value='USER'>My action</option>
          <option value='EMPLOYER'>Employer</option>
          <option value='NONE'>None</option>
        </select>
      </label>
      <label className='filter-field'>
        <span>Sort by</span>
        <select
          value={filters.sortBy}
          onChange={(event) =>
            update({ sortBy: event.target.value as ApplicationSort })
          }
        >
          <option value='last_activity_at'>Recent activity</option>
          <option value='applied_at'>Application date</option>
          <option value='company_name'>Company name</option>
        </select>
      </label>
      <label className='filter-field'>
        <span>Order</span>
        <select
          value={filters.sortOrder}
          onChange={(event) =>
            update({ sortOrder: event.target.value as SortOrder })
          }
        >
          <option value='desc'>Descending</option>
          <option value='asc'>Ascending</option>
        </select>
      </label>
    </div>
  )
}
