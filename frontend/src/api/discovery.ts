import { apiRequest } from './http'

export interface DiscoveryJob {
  id: string
  company_name: string
  job_title: string
  location: string | null
  source_url: string
  availability_status: string
  work_arrangement: string | null
  location_restrictions: string | null
  already_saved: boolean
  match: {
    score: number | null
    ranking_status: string
    eligibility_status: string
    matched_skills: string[]
    unverified_requirements: string[]
    explanations: string[]
  }
}

export interface DiscoverySearchResponse {
  items: DiscoveryJob[]
  total: number
  limit: number
  offset: number
}

export interface DiscoverySource {
  id: string
  provider: string
  company_name: string
  enabled: boolean
  last_success_at: string | null
  last_error_code: string | null
}

export interface RefreshResult {
  source_id: string
  created: number
  updated: number
  unchanged: number
  observed: number
}

export function searchDiscovery(params: Record<string, string | number>) {
  const query = new URLSearchParams(
    Object.entries(params).map(([key, value]) => [key, String(value)]),
  )
  return apiRequest<DiscoverySearchResponse>(`/api/v1/discovery/jobs?${query}`)
}

export function getDiscoverySources() {
  return apiRequest<DiscoverySource[]>('/api/v1/discovery/sources')
}

export function refreshDiscoverySource(id: string, csrfToken: string) {
  return apiRequest<RefreshResult>(`/api/v1/discovery/sources/${id}/refresh`, {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  })
}

export function saveDiscoveryJob(id: string, csrfToken: string) {
  return apiRequest<{ saved: boolean; opportunity_id: string }>(
    `/api/v1/discovery/jobs/${id}/save`,
    {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrfToken },
    },
  )
}
