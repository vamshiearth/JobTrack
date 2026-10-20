import { apiRequest, getGoogleLoginUrl } from './http'

export interface AuthenticatedUser {
  id: string
  email: string
  display_name: string | null
  csrf_token: string
}

export function getCurrentUser() {
  return apiRequest<AuthenticatedUser>('/api/v1/auth/me')
}

export function startGoogleLogin() {
  window.location.assign(getGoogleLoginUrl())
}

export function logoutUser(csrfToken: string) {
  return apiRequest<{ logged_out: boolean }>('/api/v1/auth/logout', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken, 'Content-Type': 'application/json' },
  })
}
