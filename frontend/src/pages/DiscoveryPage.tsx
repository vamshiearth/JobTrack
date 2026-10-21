import { useEffect, useRef, useState } from 'react'
import {
  getDiscoverySources,
  refreshDiscoverySource,
  saveDiscoveryJob,
  searchDiscovery,
  type DiscoveryJob,
  type DiscoverySource,
} from '../api/discovery'

interface Props {
  csrfToken: string
}

export default function DiscoveryPage({ csrfToken }: Props) {
  const [jobs, setJobs] = useState<DiscoveryJob[]>([])
  const [sources, setSources] = useState<DiscoverySource[]>([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('')
  const [remote, setRemote] = useState('')
  const [sort, setSort] = useState('match_score')
  const [offset, setOffset] = useState(0)
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [refreshing, setRefreshing] = useState<string | null>(null)
  const debounce = useRef<number | undefined>(undefined)

  async function load(currentQuery = query) {
    setLoading(true)
    setError(null)
    try {
      const result = await searchDiscovery({
        q: currentQuery,
        category,
        remote,
        sort,
        limit: 12,
        offset,
      })
      setJobs(result.items)
      setTotal(result.total)
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'Could not load discovered jobs',
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void getDiscoverySources()
      .then(setSources)
      .catch(() => undefined)
    void load()
  }, [])
  useEffect(() => {
    window.clearTimeout(debounce.current)
    debounce.current = window.setTimeout(() => {
      setOffset(0)
      void load(query)
    }, 300)
    return () => window.clearTimeout(debounce.current)
  }, [query, category, remote, sort])

  async function save(job: DiscoveryJob) {
    setSaving((state) => ({ ...state, [job.id]: true }))
    try {
      await saveDiscoveryJob(job.id, csrfToken)
      setJobs((items) =>
        items.map((item) =>
          item.id === job.id ? { ...item, already_saved: true } : item,
        ),
      )
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'Could not save opportunity',
      )
    } finally {
      setSaving((state) => ({ ...state, [job.id]: false }))
    }
  }

  async function refresh(source: DiscoverySource) {
    setRefreshing(source.id)
    setError(null)
    try {
      await refreshDiscoverySource(source.id, csrfToken)
      await Promise.all([load(), getDiscoverySources().then(setSources)])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Refresh failed')
    } finally {
      setRefreshing(null)
    }
  }

  return (
    <section className='discovery-page'>
      <div className='discovery-heading'>
        <div>
          <p className='detail-eyebrow'>DISCOVERY</p>
          <h2>Find your next strong match.</h2>
          <p>Review published roles, then save the ones worth preparing for.</p>
        </div>
        <div className='discovery-count'>{total} roles</div>
      </div>
      <div className='discovery-toolbar'>
        <input
          aria-label='Search jobs'
          placeholder='Search title or employer'
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select
          aria-label='Category'
          value={category}
          onChange={(event) => setCategory(event.target.value)}
        >
          <option value=''>All categories</option>
          <option value='CPQ'>Oracle CPQ</option>
          <option value='JAVA_BACKEND'>Java / backend</option>
          <option value='PYTHON_BACKEND'>Python / backend</option>
          <option value='GENERAL_SWE'>General software</option>
        </select>
        <select
          aria-label='Work arrangement'
          value={remote}
          onChange={(event) => setRemote(event.target.value)}
        >
          <option value=''>All work types</option>
          <option value='REMOTE'>Remote</option>
          <option value='HYBRID'>Hybrid</option>
          <option value='ONSITE'>Onsite</option>
        </select>
        <select
          aria-label='Sort'
          value={sort}
          onChange={(event) => setSort(event.target.value)}
        >
          <option value='match_score'>Best match</option>
          <option value='newest'>Newest</option>
          <option value='title'>Title</option>
        </select>
      </div>
      <div className='discovery-sources'>
        {sources.map((source) => (
          <div className='source-status' key={source.id}>
            <span>
              {source.company_name} · {source.provider}
            </span>
            <small>
              {source.last_error_code
                ? `Refresh failed: ${source.last_error_code}`
                : source.last_success_at
                  ? `Updated ${new Date(source.last_success_at).toLocaleString()}`
                  : 'Not synced'}
            </small>
            <button
              type='button'
              disabled={refreshing === source.id}
              onClick={() => void refresh(source)}
            >
              {refreshing === source.id ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        ))}
      </div>
      {error && (
        <p className='discovery-error' role='alert'>
          {error}
        </p>
      )}
      {loading ? (
        <p role='status'>Loading discovered jobs...</p>
      ) : jobs.length === 0 ? (
        <div className='discovery-empty'>
          <h3>No matching roles</h3>
          <p>Try widening the filters or refresh a source.</p>
        </div>
      ) : (
        <div className='discovery-grid'>
          {jobs.map((job) => (
            <article className='discovery-card' key={job.id}>
              <div className='card-topline'>
                <span>{job.work_arrangement ?? 'Unknown arrangement'}</span>
                <span>{job.availability_status}</span>
              </div>
              <h3>{job.job_title}</h3>
              <strong>{job.company_name}</strong>
              <p>{job.location ?? 'Location not specified'}</p>
              <div className='match-status'>
                <b>
                  {job.match.ranking_status === 'RANKED' &&
                  job.match.score !== null
                    ? `${job.match.score}/100`
                    : job.match.ranking_status}
                </b>
                <span>
                  {job.match.eligibility_status === 'UNKNOWN'
                    ? 'Eligibility unknown'
                    : job.match.eligibility_status}
                </span>
              </div>
              <p className='match-explanation'>
                {job.match.explanations[0] ?? 'No additional evidence.'}
              </p>
              <div className='card-actions'>
                <a href={job.source_url} target='_blank' rel='noreferrer'>
                  View posting
                </a>
                <button
                  type='button'
                  disabled={job.already_saved || saving[job.id]}
                  onClick={() => void save(job)}
                >
                  {job.already_saved
                    ? 'Saved'
                    : saving[job.id]
                      ? 'Saving...'
                      : 'Save opportunity'}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
      {total > 12 && (
        <div className='discovery-pagination'>
          <button
            type='button'
            disabled={offset === 0}
            onClick={() => {
              setOffset(Math.max(0, offset - 12))
              void load()
            }}
          >
            Previous
          </button>
          <span>
            {offset + 1}-{Math.min(offset + 12, total)} of {total}
          </span>
          <button
            type='button'
            disabled={offset + 12 >= total}
            onClick={() => {
              setOffset(offset + 12)
              void load()
            }}
          >
            Next
          </button>
        </div>
      )}
    </section>
  )
}
