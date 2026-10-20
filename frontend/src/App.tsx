import { useEffect, useState } from 'react'
import { getBackendHealth, type HealthResponse } from './api/client'
import './App.css'

type ConnectionState = 'checking' | 'connected' | 'disconnected'

function App() {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>('checking')
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    let active = true

    async function checkBackend() {
      try {
        const result = await getBackendHealth()

        if (!active) return

        setHealth(result)
        setConnectionState(
          result.status === 'healthy' ? 'connected' : 'disconnected',
        )
      } catch (error) {
        if (!active) return

        console.error('Backend health check failed:', error)
        setHealth(null)
        setConnectionState('disconnected')
      }
    }

    void checkBackend()

    return () => {
      active = false
    }
  }, [])

  const statusTitle =
    connectionState === 'checking'
      ? 'Checking Backend...'
      : connectionState === 'connected'
        ? 'Backend Connected'
        : 'Backend Disconnected'

  return (
    <main className='app-container'>
      <div className='app-card'>
        <div className='logo'>JT</div>
        <h1>JobTrack</h1>
        <p className='subtitle'>Intelligent Job Application Tracking System</p>
        <div className='status-card'>
          <span className={`status-indicator ${connectionState}`} />
          <div>
            <h3>{statusTitle}</h3>
            <p>
              {connectionState === 'connected'
                ? `${health?.service} - v${health?.version}`
                : connectionState === 'checking'
                  ? 'Contacting FastAPI server...'
                  : 'Unable to reach FastAPI server'}
            </p>
          </div>
        </div>
        <div className='coming-soon'>
          <h2>Your Job Search, Organized.</h2>
          <p>
            Track applications, recruiter responses, assessments, interviews,
            and offers from one dashboard.
          </p>
        </div>
        <footer>JobTrack v0.1.0 - Development Environment</footer>
      </div>
    </main>
  )
}

export default App
