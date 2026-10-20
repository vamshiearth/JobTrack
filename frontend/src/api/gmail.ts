const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface GmailConnection {
  connected: boolean
  email: string | null
  status: string
  granted_scopes: string[]
  last_synced_at: string | null
}

export interface GmailSyncStatus {
  connected: boolean
  sync_enabled: boolean
  last_successful_sync_at: string | null
  last_sync_status: string
  message_count: number
  requires_reconnection: boolean
}

export interface GmailSyncResult {
  mode: string
  messages_fetched: number
  messages_updated: number
  messages_deleted: number
  completed: boolean
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}/api/v1/gmail${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok)
    throw new Error((await response.json()).detail ?? `HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export function getGmailConnection() {
  return request<GmailConnection>('/connection')
}

export function startGmailConnection(csrfToken: string) {
  return request<{ authorization_url: string }>('/connect', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  })
}

export function disconnectGmail(csrfToken: string) {
  return request<{ status: string }>('/disconnect', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  })
}

export function getGmailSyncStatus() {
  return request<GmailSyncStatus>('/sync-status')
}

export function triggerGmailSync(csrfToken: string) {
  return request<GmailSyncResult>('/sync', {
    method: 'POST',
    headers: { 'X-CSRF-Token': csrfToken },
  })
}
