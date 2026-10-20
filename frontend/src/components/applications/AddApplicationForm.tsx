import { useState, type FormEvent } from 'react'
import {
  createApplication,
  type CreateApplicationPayload,
} from '../../api/applications'
import { ApiError } from '../../api/http'

interface Props {
  csrfToken: string
  onCreated: (applicationId: string) => void
  onCancel: () => void
}

export default function AddApplicationForm({
  csrfToken,
  onCreated,
  onCancel,
}: Props) {
  const [companyName, setCompanyName] = useState('')
  const [jobTitle, setJobTitle] = useState('')
  const [location, setLocation] = useState('')
  const [jobUrl, setJobUrl] = useState('')
  const [appliedAt, setAppliedAt] = useState('')
  const [notes, setNotes] = useState('')
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
        const url = new URL(trimmedUrl)
        if (!['http:', 'https:'].includes(url.protocol)) throw new Error()
      } catch {
        setError('Enter a valid HTTP or HTTPS job URL.')
        return
      }
    }

    const payload: CreateApplicationPayload = {
      company_name: company,
      job_title: title,
      location: location.trim() || null,
      job_url: trimmedUrl || null,
      applied_at: appliedAt || null,
      notes: notes.trim() || null,
    }

    setSaving(true)
    setError(null)
    try {
      const created = await createApplication(payload, csrfToken)
      onCreated(created.id)
    } catch (cause) {
      if (cause instanceof ApiError) {
        if (cause.status === 401) {
          setError('Your session has expired. Refresh the page and sign in.')
        } else if (cause.status === 403) {
          setError('Security verification failed. Refresh your session and retry.')
        } else if (cause.status === 422) {
          setError('Some application details were rejected. Check the fields.')
        } else {
          setError(cause.message)
        }
      } else {
        setError('Unable to save the application. Check your connection.')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className='add-application-form' onSubmit={(event) => void handleSubmit(event)}>
      <div className='form-row'><label htmlFor='company-name'>Company name *</label><input id='company-name' value={companyName} onChange={(event) => setCompanyName(event.target.value)} maxLength={255} required disabled={saving} /></div>
      <div className='form-row'><label htmlFor='job-title'>Job title *</label><input id='job-title' value={jobTitle} onChange={(event) => setJobTitle(event.target.value)} maxLength={255} required disabled={saving} /></div>
      <div className='form-row'><label htmlFor='job-location'>Location</label><input id='job-location' value={location} onChange={(event) => setLocation(event.target.value)} placeholder='Boston, MA / Remote' disabled={saving} /></div>
      <div className='form-row'><label htmlFor='job-url'>Job posting URL</label><input id='job-url' type='url' value={jobUrl} onChange={(event) => setJobUrl(event.target.value)} placeholder='https://...' disabled={saving} /></div>
      <div className='form-row'><label htmlFor='applied-at'>Applied date</label><input id='applied-at' type='date' value={appliedAt} onChange={(event) => setAppliedAt(event.target.value)} disabled={saving} /></div>
      <div className='form-row'><label htmlFor='application-notes'>Notes</label><textarea id='application-notes' rows={4} value={notes} onChange={(event) => setNotes(event.target.value)} disabled={saving} /></div>
      {error && <p role='alert' className='form-error'>{error}</p>}
      <div className='form-actions'><button type='button' onClick={onCancel} disabled={saving}>Cancel</button><button type='submit' className='primary-action' disabled={saving || !companyName.trim() || !jobTitle.trim()}>{saving ? 'Saving...' : 'Save application'}</button></div>
    </form>
  )
}