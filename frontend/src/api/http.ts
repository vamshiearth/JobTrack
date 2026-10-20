const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
).replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  code?: string

  constructor(status: number, message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string }
  detail?: string
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: { Accept: 'application/json', ...options.headers },
  })

  if (!response.ok) {
    let body: ErrorBody = {}
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      // Keep the HTTP status as the useful error when no JSON exists.
    }
    throw new ApiError(
      response.status,
      body.error?.message ??
        body.detail ??
        `Request failed (${response.status})`,
      body.error?.code,
    )
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function getGoogleLoginUrl() {
  return `${API_BASE_URL}/api/v1/auth/google/login`
}
