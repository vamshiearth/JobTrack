import type { ActionOwner, ApplicationStage } from '../types/dashboard'
import type { TimelineEventKind } from '../types/timeline'
import { apiRequest } from './http'

export interface ApiApplication {
  id: string
  company_name: string
  job_title: string
  location: string | null
  job_url: string | null
  applied_at: string | null
  application_source: string
  current_stage: ApplicationStage
  next_action_owner: ActionOwner
  notes: string | null
  last_activity_at: string
  created_at: string
  updated_at: string
}

export interface ApiApplicationList {
  items: ApiApplication[]
  total: number
  page: number
  page_size: number
}

export interface ApiTimelineEvent {
  id: string
  job_application_id: string
  event_kind: TimelineEventKind
  interview_round: number | null
  origin: string
  verified_by_user: boolean
  details: Record<string, unknown> | null
  occurred_at: string
  recorded_at: string
}

export interface ApiTimelineList {
  items: ApiTimelineEvent[]
  total: number
}

export interface ApplicationQuery {
  q: string
  stage: ApplicationStage | 'ALL'
  nextActionOwner: ActionOwner | 'ALL'
  page: number
  pageSize: number
  sortBy: 'last_activity_at' | 'applied_at' | 'company_name'
  sortOrder: 'asc' | 'desc'
}

export interface CreateApplicationPayload {
  company_name: string
  job_title: string
  location?: string | null
  job_url?: string | null
  applied_at?: string | null
  notes?: string | null
}

export function createApplication(
  payload: CreateApplicationPayload,
  csrfToken: string,
) {
  return apiRequest<ApiApplication>('/api/v1/applications', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify(payload),
  })
}

export function getApplications(query: ApplicationQuery) {
  const params = new URLSearchParams({
    page: String(query.page),
    page_size: String(query.pageSize),
    sort_by: query.sortBy,
    sort_order: query.sortOrder,
  })
  if (query.q.trim()) params.set('q', query.q.trim())
  if (query.stage !== 'ALL') params.set('stage', query.stage)
  if (query.nextActionOwner !== 'ALL')
    params.set('next_action_owner', query.nextActionOwner)
  return apiRequest<ApiApplicationList>(`/api/v1/applications?${params}`)
}

export function getApplication(id: string) {
  return apiRequest<ApiApplication>(
    `/api/v1/applications/${encodeURIComponent(id)}`,
  )
}

export function getApplicationEvents(id: string) {
  return apiRequest<ApiTimelineList>(
    `/api/v1/applications/${encodeURIComponent(id)}/events`,
  )
}
