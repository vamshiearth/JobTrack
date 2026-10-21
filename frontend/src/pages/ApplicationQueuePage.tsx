import { useEffect, useState } from 'react'
import {
  confirmSubmission,
  createHandoff,
  getPreparations,
  updatePreparation,
  type Handoff,
  type Preparation,
} from '../api/applicationQueue'
import SubmissionConfirmation from '../components/applications/SubmissionConfirmation'

interface Props {
  csrfToken: string
  onViewApplication: (id: string) => void
}

export default function ApplicationQueuePage({
  csrfToken,
  onViewApplication,
}: Props) {
  const [items, setItems] = useState<Preparation[]>([])
  const [handoffs, setHandoffs] = useState<Record<string, Handoff>>({})
  const [answers, setAnswers] = useState<
    Record<string, Record<string, string>>
  >({})
  const [message, setMessage] = useState<string | null>(null)

  async function refresh() {
    setItems(await getPreparations())
  }
  useEffect(() => {
    async function loadQueue() {
      try {
        await refresh()
      } catch {
        setMessage('The application queue could not be loaded.')
      }
    }

    void loadQueue()
  }, [])

  async function resolveAndApprove(item: Preparation) {
    const resolved = item.application_answers.map((answer) => ({
      ...answer,
      answer: answer.answer ?? answers[item.id]?.[answer.question_key] ?? null,
      status:
        (answer.answer ?? answers[item.id]?.[answer.question_key])
          ? 'RESOLVED'
          : answer.status,
    }))
    if (resolved.some((answer) => !answer.answer)) {
      setMessage('Answer every required question before approval.')
      return
    }
    await updatePreparation(
      item.id,
      { application_answers: resolved, status: 'APPROVED' },
      csrfToken,
    )
    await refresh()
  }

  async function openEmployerSite(item: Preparation) {
    const handoff = await createHandoff(item.id, csrfToken)
    setHandoffs((current) => ({ ...current, [item.id]: handoff }))
    window.open(handoff.source_url_snapshot, '_blank', 'noopener,noreferrer')
  }

  async function confirm(item: Preparation, handoff: Handoff) {
    const result = await confirmSubmission(
      item.id,
      {
        expected_revision: item.draft_revision,
        idempotency_key: `queue-${item.id}-${item.draft_revision}`,
        user_confirmed_submission: true,
        handoff_id: handoff.id,
      },
      csrfToken,
    )
    setMessage('Submission tracked.')
    onViewApplication(result.job_application_id)
  }

  return (
    <section className='review-queue-page'>
      <div className='applications-intro'>
        <div>
          <p className='detail-eyebrow'>WORKFLOW</p>
          <h2>Application Queue</h2>
          <p>
            Review, hand off, and record applications only after you submit them
            yourself.
          </p>
        </div>
      </div>
      {message && <p role='status'>{message}</p>}
      {items.length === 0 && (
        <p>No preparation packages are waiting for review.</p>
      )}
      <div className='review-card-list'>
        {items.map((item) => {
          const handoff = handoffs[item.id]
          const unresolved = item.application_answers.some(
            (answer) =>
              answer.status === 'NEEDS_USER_INPUT' || answer.answer === null,
          )
          return (
            <article className='review-card' key={item.id}>
              <p className='detail-eyebrow'>{item.status}</p>
              <h3>Preparation package</h3>
              <p>Revision {item.draft_revision}</p>
              {unresolved && (
                <p>
                  Required answers are unresolved. Review each answer before
                  approval.
                </p>
              )}
              {unresolved &&
                item.application_answers.map(
                  (answer) =>
                    answer.answer === null && (
                      <label key={answer.question_key}>
                        {answer.question_key}
                        <input
                          value={answers[item.id]?.[answer.question_key] ?? ''}
                          onChange={(event) =>
                            setAnswers((current) => ({
                              ...current,
                              [item.id]: {
                                ...current[item.id],
                                [answer.question_key]: event.target.value,
                              },
                            }))
                          }
                        />
                      </label>
                    ),
                )}
              {item.status !== 'APPROVED' && (
                <button
                  type='button'
                  className='secondary-button'
                  onClick={() => void resolveAndApprove(item)}
                >
                  Resolve answers and approve
                </button>
              )}
              {item.status === 'APPROVED' && !handoff && (
                <button
                  type='button'
                  className='primary-button'
                  onClick={() => void openEmployerSite(item)}
                >
                  Open employer site
                </button>
              )}
              {handoff && (
                <>
                  <p>
                    Employer site presented:{' '}
                    {new URL(handoff.source_url_snapshot).host}
                  </p>
                  <a
                    href={handoff.source_url_snapshot}
                    target='_blank'
                    rel='noreferrer'
                  >
                    Open employer site again
                  </a>
                  <SubmissionConfirmation
                    disabled={false}
                    onConfirm={() => void confirm(item, handoff)}
                  />
                </>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
