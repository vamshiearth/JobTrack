import { useEffect, useState } from 'react'
import { getApplications, type ApiApplication } from '../api/applications'
import {
  approveReview,
  getReviewItems,
  rejectReview,
  type ReviewItem,
} from '../api/reviewItems'
import { ApiError } from '../api/http'

interface Props {
  csrfToken: string
  onViewApplication: (id: string) => void
}

export default function ReviewQueuePage({
  csrfToken,
  onViewApplication,
}: Props) {
  const [reviews, setReviews] = useState<ReviewItem[]>([])
  const [applications, setApplications] = useState<ApiApplication[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [selected, setSelected] = useState<Record<string, string>>({})
  const [rounds, setRounds] = useState<Record<string, string>>({})

  async function load() {
    try {
      const [reviewResult, applicationResult] = await Promise.all([
        getReviewItems(),
        getApplications({
          q: '',
          stage: 'ALL',
          nextActionOwner: 'ALL',
          page: 1,
          pageSize: 100,
          sortBy: 'company_name',
          sortOrder: 'asc',
        }),
      ])
      setReviews(reviewResult.items)
      setApplications(applicationResult.items)
      setError(null)
    } catch {
      setError('Unable to load the review queue.')
    }
  }
  useEffect(() => {
    let active = true
    queueMicrotask(() => {
      if (active) void load()
    })
    return () => {
      active = false
    }
  }, [])

  async function decide(review: ReviewItem, action: 'approve' | 'reject') {
    if (busy) return
    const applicationId =
      selected[review.id] ?? review.candidate_application_id ?? ''
    if (action === 'approve' && !applicationId) {
      setError('Choose an application before approving.')
      return
    }
    let interviewRound: number | null = null
    if (
      action === 'approve' &&
      review.proposed_event_type === 'INTERVIEW_SCHEDULED'
    ) {
      interviewRound = Number(rounds[review.id])
      if (!Number.isInteger(interviewRound) || interviewRound < 1) {
        setError('Enter the confirmed interview round.')
        return
      }
    }
    if (
      action === 'approve' &&
      !window.confirm(
        `Apply ${review.proposed_event_type ?? 'this update'} to the selected application?`,
      )
    )
      return
    setBusy(review.id)
    setError(null)
    try {
      if (action === 'approve')
        await approveReview(
          review.id,
          { application_id: applicationId, interview_round: interviewRound },
          csrfToken,
        )
      else await rejectReview(review.id, csrfToken)
      await load()
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : 'The decision could not be confirmed.',
      )
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className='review-queue-page'>
      <div className='live-page-heading'>
        <div>
          <h2>Recruitment Reviews</h2>
          <p>Review stored Gmail metadata before it changes your timeline.</p>
        </div>
        <button type='button' onClick={() => void load()}>
          Refresh
        </button>
      </div>
      {error && <p role='alert'>{error}</p>}
      {reviews.length === 0 ? (
        <p role='status'>No pending reviews found.</p>
      ) : (
        <div className='review-card-list'>
          {reviews.map((review) => {
            const applicationId =
              selected[review.id] ?? review.candidate_application_id ?? ''
            return (
              <article className='review-card' key={review.id}>
                <h3>{review.category.replaceAll('_', ' ')}</h3>
                <p>
                  <strong>Subject:</strong>{' '}
                  {review.evidence.subject ?? 'Unavailable'}
                </p>
                <p>
                  <strong>From:</strong>{' '}
                  {review.evidence.sender ?? 'Unavailable'}
                </p>
                <p>
                  <strong>Proposed event:</strong>{' '}
                  {review.proposed_event_type ?? 'No application event'}
                </p>
                <ul>
                  {review.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                <label>
                  Application
                  <select
                    value={applicationId}
                    onChange={(event) =>
                      setSelected({
                        ...selected,
                        [review.id]: event.target.value,
                      })
                    }
                  >
                    <option value=''>Select an owned application</option>
                    {applications.map((application) => (
                      <option key={application.id} value={application.id}>
                        {application.company_name} - {application.job_title}
                      </option>
                    ))}
                  </select>
                </label>
                {review.proposed_event_type === 'INTERVIEW_SCHEDULED' && (
                  <label>
                    Confirmed interview round
                    <input
                      type='number'
                      min='1'
                      value={rounds[review.id] ?? ''}
                      onChange={(event) =>
                        setRounds({
                          ...rounds,
                          [review.id]: event.target.value,
                        })
                      }
                    />
                  </label>
                )}
                <div className='review-actions'>
                  <button
                    type='button'
                    disabled={busy !== null}
                    onClick={() => void decide(review, 'reject')}
                  >
                    Reject
                  </button>
                  {review.proposed_event_type && (
                    <button
                      type='button'
                      disabled={busy !== null}
                      onClick={() => void decide(review, 'approve')}
                    >
                      {busy === review.id ? 'Processing...' : 'Approve update'}
                    </button>
                  )}
                  {review.candidate_application_id && (
                    <button
                      type='button'
                      onClick={() =>
                        onViewApplication(review.candidate_application_id!)
                      }
                    >
                      View application
                    </button>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
