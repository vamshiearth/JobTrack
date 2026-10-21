import { apiRequest } from './http'

export type PreparationStatus =
  | 'DRAFT'
  | 'NEEDS_REVIEW'
  | 'APPROVED'
  | 'STALE'
  | 'ARCHIVED'

export interface Preparation {
  id: string
  opportunity_id: string
  draft_revision: number
  approved_revision: number | null
  status: PreparationStatus
  application_answers: Array<{
    question_key: string
    answer: string | null
    status: string
  }>
  created_at: string
  updated_at: string
}

export interface Handoff {
  id: string
  preparation_id: string
  approved_revision: number
  source_url_snapshot: string
  opened_at: string
  created_at: string
}

export interface SubmissionConfirmation {
  id: string
  preparation_id: string
  handoff_id: string | null
  job_application_id: string
  confirmation_method: string
  confirmed_at: string
  idempotency_key: string
}

export function getPreparations() {
  return apiRequest<Preparation[]>('/api/v1/preparations')
}

export function updatePreparation(
  id: string,
  payload: Partial<Pick<Preparation, 'application_answers' | 'status'>>,
  csrfToken: string,
) {
  return apiRequest<Preparation>(
    `/api/v1/preparations/${encodeURIComponent(id)}`,
    {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify(payload),
    },
  )
}

export function createHandoff(id: string, csrfToken: string) {
  return apiRequest<Handoff>(
    `/api/v1/preparations/${encodeURIComponent(id)}/handoff`,
    {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrfToken },
    },
  )
}

export function confirmSubmission(
  id: string,
  payload: {
    expected_revision: number
    idempotency_key: string
    user_confirmed_submission: boolean
    handoff_id: string
  },
  csrfToken: string,
) {
  return apiRequest<SubmissionConfirmation>(
    `/api/v1/preparations/${encodeURIComponent(id)}/confirm-submission`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken,
      },
      body: JSON.stringify(payload),
    },
  )
}
