import { useState, type FormEvent } from 'react'
import {
  updateApplication,
  type ApiApplication,
  type UpdateApplicationPayload,
} from '../../api/applications'
import { ApiError } from '../../api/http'

interface Props {
  application: ApiApplication
  csrfToken: string
  onSaved: () => void
  onCancel: () => void
}

function toDateInput(value: string | null) {
  return value ? value.slice(0, 10) : ''
}

function optionalText(value: string) {
  return value.trim() || null
}

export default function EditApplicationForm({
  application,
  csrfToken,
  onSaved,
  onCancel,
}: Props) {
  const [companyName, setCompanyName] = useState(application.company_name)
  const [jobTitle, setJobTitle] = useState(application.job_title)
  const [location, setLocation] = useState(application.location ?? '')
  const [jobUrl, setJobUrl] = useState(application.job_url ?? '')
  const [appliedAt, setAppliedAt] = useState(
    toDateInput(application.applied_at),
  )
  const [notes, setNotes] = useState(application.notes ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (saving) return

    const company = companyName.trim()
    const title = jobTitle.trim()
    if (!company || !title) {
      setError('Company and job title are required.')
      return
    }

    const trimmedUrl = jobUrl.trim()
    if (trimmedUrl) {
      try {
        const parsed = new URL(trimmedUrl)
        if (!['http:', 'https:'].includes(parsed.protocol)) throw new Error()
      } catch {
        setError('Enter a valid HTTP or HTTPS job URL.')
        return
      }
    }

    const payload: UpdateApplicationPayload = {
      company_name: company,
      job_title: title,
      location: optionalText(location),
      job_url: optionalText(jobUrl),
      applied_at: appliedAt || null,
      notes: optionalText(notes),
    }

    setSaving(true)
    setError(null)
    try {
      await updateApplication(application.id, payload, csrfToken)
      onSaved()
    } catch (cause) {
      if (cause instanceof ApiError) {
        if (cause.status === 401)
          setError('Your session has expired. Sign in again before saving.')
        else if (cause.status === 403)
          setError('Security verification failed. Refresh your session.')
        else if (cause.status === 404)
          setError(
            'This application could not be found or is no longer accessible.',
          )
        else if (cause.status === 409)
          setError(
            'The application could not be updated because of a conflict.',
          )
        else if (cause.status === 422)
          setError('Some values were rejected. Check the fields and try again.')
        else setError(cause.message)
      } else {
        setError('Unable to save changes. Check your connection.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <form
      className='add-application-form'
      onSubmit={(event) => void handleSubmit(event)}
    >
      <div className='form-row'>
        <label htmlFor='edit-company'>Company name *</label>
        <input
          id='edit-company'
          value={companyName}
          onChange={(event) => setCompanyName(event.target.value)}
          maxLength={255}
          required
          disabled={saving}
        />
      </div>
      <div className='form-row'>
        <label htmlFor='edit-title'>Job title *</label>
        <input
          id='edit-title'
          value={jobTitle}
          onChange={(event) => setJobTitle(event.target.value)}
          maxLength={255}
          required
          disabled={saving}
        />
      </div>
      <div className='form-row'>
        <label htmlFor='edit-location'>Location</label>
        <input
          id='edit-location'
          value={location}
          onChange={(event) => setLocation(event.target.value)}
          disabled={saving}
        />
      </div>
      <div className='form-row'>
        <label htmlFor='edit-job-url'>Job posting URL</label>
        <input
          id='edit-job-url'
          type='url'
          value={jobUrl}
          onChange={(event) => setJobUrl(event.target.value)}
          disabled={saving}
        />
      </div>
      <div className='form-row'>
        <label htmlFor='edit-applied-date'>Applied date</label>
        <input
          id='edit-applied-date'
          type='date'
          value={appliedAt}
          onChange={(event) => setAppliedAt(event.target.value)}
          disabled={saving}
        />
      </div>
      <div className='form-row'>
        <label htmlFor='edit-notes'>Notes</label>
        <textarea
          id='edit-notes'
          rows={4}
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          disabled={saving}
        />
      </div>
      <p className='form-helper-text'>
        Recruitment stage and next action are managed through application
        timeline events.
      </p>
      {error && (
        <p role='alert' className='form-error'>
          {error}
        </p>
      )}
      <div className='form-actions'>
        <button type='button' onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button
          type='submit'
          className='primary-action'
          disabled={saving || !companyName.trim() || !jobTitle.trim()}
        >
          {saving ? 'Saving changes...' : 'Save changes'}
        </button>
      </div>
    </form>
  )
}
