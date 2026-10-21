import { apiRequest } from './http'

export interface CandidateProfile {
  id: string
  user_id: string
  skills: string[]
  experience_summary: string | null
  target_roles: string[]
  preferred_locations: string[]
  remote_preference: string | null
  resume_version: string
  revision: number
}

export interface CandidateProfileInput {
  skills: string[]
  experience_summary: string | null
  target_roles: string[]
  preferred_locations: string[]
  remote_preference: string | null
  resume_version: string
}

export function getCandidateProfile() {
  return apiRequest<CandidateProfile>('/api/v1/candidate-profile')
}

export function saveCandidateProfile(
  input: CandidateProfileInput,
  csrfToken: string,
) {
  return apiRequest<CandidateProfile>('/api/v1/candidate-profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
    body: JSON.stringify(input),
  })
}
