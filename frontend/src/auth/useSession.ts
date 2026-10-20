import { useCallback, useEffect, useRef, useState } from 'react'
import { getCurrentUser, logoutUser, type AuthenticatedUser } from '../api/auth'
import { ApiError } from '../api/http'

type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'error'

export function useSession() {
  const [status, setStatus] = useState<SessionStatus>('loading')
  const [user, setUser] = useState<AuthenticatedUser | null>(null)
  const [error, setError] = useState<string | null>(null)
  const requestId = useRef(0)

  const refresh = useCallback(async () => {
    const currentRequest = ++requestId.current
    setStatus('loading')
    setError(null)
    try {
      const nextUser = await getCurrentUser()
      if (currentRequest !== requestId.current) return
      setUser(nextUser)
      setStatus('authenticated')
    } catch (cause) {
      if (currentRequest !== requestId.current) return
      setUser(null)
      if (cause instanceof ApiError && cause.status === 401) {
        setStatus('unauthenticated')
      } else {
        setStatus('error')
        setError('Unable to verify your session. Check the backend connection.')
      }
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => void refresh())
  }, [refresh])

  const logout = useCallback(async () => {
    if (!user) return
    ++requestId.current
    setError(null)
    try {
      await logoutUser(user.csrf_token)
      setUser(null)
      setStatus('unauthenticated')
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) {
        setUser(null)
        setStatus('unauthenticated')
        return
      }
      setError('Logout could not be confirmed. Please try again.')
      throw cause
    }
  }, [user])

  return { status, user, error, refresh, logout }
}
