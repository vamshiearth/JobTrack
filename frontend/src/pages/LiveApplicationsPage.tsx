import { useEffect, useState } from 'react'
import {
  getApplications,
  type ApiApplicationList,
  type ApplicationQuery,
} from '../api/applications'
import { ApiError } from '../api/http'

interface Props {
  onViewDetails: (id: string) => void
}

const initialQuery: ApplicationQuery = {
  q: '',
  stage: 'ALL',
  nextActionOwner: 'ALL',
  page: 1,
  pageSize: 10,
  sortBy: 'last_activity_at',
  sortOrder: 'desc',
}

export default function LiveApplicationsPage({ onViewDetails }: Props) {
  const [query, setQuery] = useState(initialQuery)
  const [data, setData] = useState<ApiApplicationList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let current = true
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const result = await getApplications(query)
        if (current) setData(result)
      } catch (cause) {
        if (current) {
          setData(null)
          setError(
            cause instanceof ApiError && cause.status === 401
              ? 'Your session has expired. Please sign in again.'
              : 'Applications could not be loaded.',
          )
        }
      } finally {
        if (current) setLoading(false)
      }
    }
    void load()
    return () => {
      current = false
    }
  }, [query])

  function change(changes: Partial<ApplicationQuery>) {
    setQuery((current) => ({ ...current, ...changes, page: 1 }))
  }

  const totalPages = data
    ? Math.max(1, Math.ceil(data.total / data.page_size))
    : 1

  return (
    <section className='applications-page live-page'>
      <div className='applications-intro'>
        <div>
          <h2>My Applications</h2>
          <p>Your saved applications from JobTrack.</p>
        </div>
      </div>
      <div className='applications-panel'>
        <div className='applications-toolbar'>
          <label className='filter-field search-field'>
            <span>Company or role</span>
            <input
              type='search'
              value={query.q}
              onChange={(event) => change({ q: event.target.value })}
              placeholder='Search applications'
            />
          </label>
          <label className='filter-field'>
            <span>Stage</span>
            <select
              value={query.stage}
              onChange={(event) =>
                change({
                  stage: event.target.value as ApplicationQuery['stage'],
                })
              }
            >
              <option value='ALL'>All stages</option>
              {[
                'APPLIED',
                'SCREENING',
                'ASSESSMENT',
                'INTERVIEW',
                'OFFER',
                'REJECTED',
                'WITHDRAWN',
              ].map((stage) => (
                <option key={stage} value={stage}>
                  {stage}
                </option>
              ))}
            </select>
          </label>
          <label className='filter-field'>
            <span>Next action</span>
            <select
              value={query.nextActionOwner}
              onChange={(event) =>
                change({
                  nextActionOwner: event.target
                    .value as ApplicationQuery['nextActionOwner'],
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
            <span>Sort</span>
            <select
              value={query.sortBy}
              onChange={(event) =>
                change({
                  sortBy: event.target.value as ApplicationQuery['sortBy'],
                })
              }
            >
              <option value='last_activity_at'>Recent activity</option>
              <option value='applied_at'>Application date</option>
              <option value='company_name'>Company</option>
            </select>
          </label>
          <label className='filter-field'>
            <span>Order</span>
            <select
              value={query.sortOrder}
              onChange={(event) =>
                change({
                  sortOrder: event.target
                    .value as ApplicationQuery['sortOrder'],
                })
              }
            >
              <option value='desc'>Descending</option>
              <option value='asc'>Ascending</option>
            </select>
          </label>
        </div>
        {loading ? (
          <p role='status'>Loading applications...</p>
        ) : error ? (
          <p role='alert'>{error}</p>
        ) : !data || data.items.length === 0 ? (
          <div className='applications-empty' role='status'>
            <h3>No applications found</h3>
            <p>Your account has no applications matching these filters.</p>
          </div>
        ) : (
          <div className='applications-table-scroll'>
            <table className='applications-table'>
              <thead>
                <tr>
                  <th scope='col'>Company / Role</th>
                  <th scope='col'>Stage</th>
                  <th scope='col'>Next Action</th>
                  <th scope='col'>Details</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((application) => (
                  <tr key={application.id}>
                    <td>
                      <div className='table-job-details'>
                        <strong>{application.job_title}</strong>
                        <span>{application.company_name}</span>
                      </div>
                    </td>
                    <td>{application.current_stage}</td>
                    <td>{application.next_action_owner}</td>
                    <td>
                      <button
                        type='button'
                        className='view-details-button'
                        onClick={() => onViewDetails(application.id)}
                      >
                        View details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!loading && !error && data && (
          <nav
            className='applications-pagination'
            aria-label='Application pages'
          >
            <span>{data.total} matching applications</span>
            <div className='pagination-buttons'>
              <button
                type='button'
                disabled={query.page <= 1}
                onClick={() =>
                  setQuery((current) => ({
                    ...current,
                    page: current.page - 1,
                  }))
                }
              >
                Previous
              </button>
              <span>
                Page {data.page} of {totalPages}
              </span>
              <button
                type='button'
                disabled={data.page >= totalPages}
                onClick={() =>
                  setQuery((current) => ({
                    ...current,
                    page: current.page + 1,
                  }))
                }
              >
                Next
              </button>
            </div>
          </nav>
        )}
      </div>
    </section>
  )
}
