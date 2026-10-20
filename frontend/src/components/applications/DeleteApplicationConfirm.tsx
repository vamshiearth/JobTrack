import { useState } from 'react'
import { deleteApplication, type ApiApplication } from '../../api/applications'
import { ApiError } from '../../api/http'

interface Props {
  application: ApiApplication
  csrfToken: string
  onCancel: () => void
  onDeleted: () => void
}

export default function DeleteApplicationConfirm({
  application,
  csrfToken,
  onCancel,
  onDeleted,
}: Props) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function confirmDeletion() {
    if (deleting) return

    setDeleting(true)
    setError(null)
    try {
      await deleteApplication(application.id, csrfToken)
      onDeleted()
    } catch (cause) {
      if (cause instanceof ApiError) {
        if (cause.status === 401)
          setError('Your session expired. Sign in again before deleting.')
        else if (cause.status === 403)
          setError('Security verification failed. Refresh your session.')
        else if (cause.status === 404)
          setError('This application was not found or is no longer accessible.')
        else if (cause.status === 409)
          setError('This application cannot be deleted in its current state.')
        else setError(cause.message)
      } else {
        setError(
          'Deletion could not be confirmed. Check the application list before trying again.',
        )
      }
    } finally {
      setDeleting(false)
    }
  }

  return (
    <section
      className='delete-confirm-panel'
      aria-labelledby='delete-confirm-title'
      aria-describedby='delete-confirm-description'
    >
      <h3 id='delete-confirm-title'>Delete application?</h3>
      <p id='delete-confirm-description'>
        You are about to permanently delete{' '}
        <strong>{application.job_title}</strong> at{' '}
        <strong>{application.company_name}</strong>.
      </p>
      <p>
        This will also remove its recruitment timeline. This action cannot be
        undone.
      </p>
      {error && (
        <p role='alert' className='form-error'>
          {error}
        </p>
      )}
      <div className='form-actions'>
        <button type='button' onClick={onCancel} disabled={deleting}>
          Cancel
        </button>
        <button
          type='button'
          className='danger-action'
          onClick={() => void confirmDeletion()}
          disabled={deleting}
        >
          {deleting ? 'Deleting...' : 'Delete permanently'}
        </button>
      </div>
    </section>
  )
}
