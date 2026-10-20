import { useEffect, useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import ApplicationsPage from './pages/ApplicationsPage'
import DashboardPage from './pages/DashboardPage'
import InboxPage from './pages/InboxPage'
import SettingsPage from './pages/SettingsPage'
import TimelinePage from './pages/TimelinePage'
import { getBackendHealth } from './api/client'
import type { PageId } from './types/navigation'
import './App.css'

type BackendStatus = 'checking' | 'connected' | 'disconnected'

function App() {
  const [activePage, setActivePage] = useState<PageId>('dashboard')
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking')

  useEffect(() => {
    let active = true

    async function checkBackend() {
      try {
        const result = await getBackendHealth()

        if (!active) return

        setBackendStatus(
          result.status === 'healthy' ? 'connected' : 'disconnected',
        )
      } catch (error) {
        if (!active) return

        console.error('Backend health check failed:', error)
        setBackendStatus('disconnected')
      }
    }

    void checkBackend()

    return () => {
      active = false
    }
  }, [])

  function renderPage() {
    switch (activePage) {
      case 'dashboard':
        return <DashboardPage />
      case 'applications':
        return <ApplicationsPage />
      case 'timeline':
        return <TimelinePage />
      case 'inbox':
        return <InboxPage />
      case 'settings':
        return <SettingsPage />
    }
  }

  return (
    <div className='app-layout'>
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <div className='app-main'>
        <Header activePage={activePage} backendStatus={backendStatus} />
        <main className='app-content'>{renderPage()}</main>
      </div>
    </div>
  )
}

export default App
