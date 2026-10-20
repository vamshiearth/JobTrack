const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface HealthResponse {
  status: string
  service: string
  version: string
}

export async function getBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: 'GET',
    credentials: 'include',
  })

  if (!response.ok) {
    throw new Error(`Backend returned HTTP ${response.status}`)
  }

  return response.json() as Promise<HealthResponse>
}
