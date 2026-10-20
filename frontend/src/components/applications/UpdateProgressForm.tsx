import { useRef, useState, type FormEvent } from 'react'
import {
  createApplicationEvent,
  type ManualEventType,
} from '../../api/applications'
import { ApiError } from '../../api/http'

interface Props {
  applicationId: string
  csrfToken: string
  onSaved: () => void
  onCancel: () => void
}

const options: { value: ManualEventType; label: string }[] = [
  { value: 'RECRUITER_CONTACTED', label: 'Recruiter contacted' },
  { value: 'ASSESSMENT_INVITED', label: 'Assessment invited' },
  { value: 'ASSESSMENT_COMPLETED', label: 'Assessment completed' },
  { value: 'INTERVIEW_SCHEDULED', label: 'Interview scheduled' },
  { value: 'INTERVIEW_COMPLETED', label: 'Interview completed' },
  { value: 'OFFER_RECEIVED', label: 'Offer received' },
  { value: 'REJECTION_RECEIVED', label: 'Rejection received' },
  { value: 'APPLICATION_WITHDRAWN', label: 'Application withdrawn' },
]

function isInterview(type: ManualEventType) {
  return type === 'INTERVIEW_SCHEDULED' || type === 'INTERVIEW_COMPLETED'
}

export default function UpdateProgressForm({
  applicationId,
  csrfToken,
  onSaved,
  onCancel,
}: Props) {
  const [eventKind, setEventKind] = useState<ManualEventType>(
    'RECRUITER_CONTACTED',
  )
  const [interviewRound, setInterviewRound] = useState(1)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pendingRequest = useRef<{
    key: string
    kind: ManualEventType
    round: number | null
    occurredAt: string
  } | null>(null)

  function changeKind(value: ManualEventType) {
    setEventKind(value)
    pendingRequest.current = null
    setError(null)
  }

  function changeRound(value: number) {
    setInterviewRound(value)
    pendingRequest.current = null
    setError(null)
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving) return

    const round = isInterview(eventKind) ? interviewRound : null
    if (round !== null && (!Number.isInteger(round) || round < 1)) {
      setError('Choose a valid interview round.')
      return
    }

    if (
      !pendingRequest.current ||
      pendingRequest.current.kind !== eventKind ||
      pendingRequest.current.round !== round
    ) {
      pendingRequest.current = {
        key: crypto.randomUUID(),
        kind: eventKind,
        round,
        occurredAt: new Date().toISOString(),
      }
    }

    const request = pendingRequest.current
    setSaving(true)
    setError(null)
    try {
      await createApplicationEvent(
        applicationId,
        {
          event_kind: request.kind,
          interview_round: request.round,
          occurred_at: request.occurredAt,
          client_request_id: request.key,
        },
        csrfToken,
      )
      pendingRequest.current = null
      onSaved()
    } catch (cause) {
      if (cause instanceof ApiError) {
        if (cause.status === 401)
          setError('Your session expired. Sign in again.')
        else if (cause.status === 403)
          setError('Security verification failed. Refresh your session.')
        else if (cause.status === 404)
          setError('This application is no longer accessible.')
        else if (cause.status === 409 || cause.status === 400)
          setError(
            cause.message ||
              'This event is not allowed in the current recruitment stage.',
          )
        else if (cause.status === 422)
          setError('The event details did not pass validation.')
        else setError(cause.message)
      } else {
        setError(
          'The result could not be confirmed. Retry without changing the event to avoid creating a duplicate.',
        )
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      className='add-application-form'
      onSubmit={(event) => void submit(event)}
    >
      <div className='form-row'>
        <label htmlFor='progress-event'>Recruitment event</label>
        <select
          id='progress-event'
          value={eventKind}
          disabled={saving}
          onChange={(event) =>
            changeKind(event.target.value as ManualEventType)
          }
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      {isInterview(eventKind) && (
        <div className='form-row'>
          <label htmlFor='interview-round'>Interview round</label>
          <input
            id='interview-round'
            type='number'
            min={1}
            step={1}
            required
            value={interviewRound}
            disabled={saving}
            onChange={(event) => changeRound(Number(event.target.value))}
          />
        </div>
      )}
      <p className='form-helper-text'>
        The backend validates event order and updates the application stage
        automatically.
      </p>
      {error && (
        <p role='alert' className='form-error'>
          {error}
        </p>
      )}
      <div className='form-actions'>
        <button type='button' disabled={saving} onClick={onCancel}>
          Cancel
        </button>
        <button className='primary-action' type='submit' disabled={saving}>
          {saving ? 'Recording...' : 'Record progress'}
        </button>
      </div>
    </form>
  )
}
