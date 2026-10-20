import { apiRequest } from './http'

export type ReviewStatus = 'PENDING' | 'APPROVED' | 'REJECTED'
export interface ReviewEvidence {
  sender: string | null
  subject: string | null
  received_at: string
}
export interface ReviewItem {
  id: string
  status: ReviewStatus
  category: string
  candidate_application_id: string | null
  proposed_event_type: string | null
  reasons: string[]
  evidence: ReviewEvidence
  created_at: string
  decided_at: string | null
}
export interface ReviewItemList {
  items: ReviewItem[]
  total: number
  page: number
  page_size: number
}
export interface ReviewDecision {
  review_id: string
  status: ReviewStatus
  application_id: string | null
  created_event_id: string | null
}
export interface ApproveReviewPayload {
  application_id: string
  interview_round?: number | null
}

export function getReviewItems(
  status: ReviewStatus = 'PENDING',
  page = 1,
  pageSize = 10,
) {
  const params = new URLSearchParams({
    status,
    page: String(page),
    page_size: String(pageSize),
  })
  return apiRequest<ReviewItemList>(`/api/v1/review-items?${params}`)
}

export function approveReview(
  id: string,
  payload: ApproveReviewPayload,
  csrfToken: string,
) {
  return apiRequest<ReviewDecision>(
    `/api/v1/review-items/${encodeURIComponent(id)}/approve`,
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

export function rejectReview(id: string, csrfToken: string) {
  return apiRequest<ReviewDecision>(
    `/api/v1/review-items/${encodeURIComponent(id)}/reject`,
    { method: 'POST', headers: { 'X-CSRF-Token': csrfToken } },
  )
}
