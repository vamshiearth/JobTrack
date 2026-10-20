import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import InboxPage from './pages/InboxPage'
import SettingsPage from './pages/SettingsPage'
import LiveApplicationsPage from './pages/LiveApplicationsPage'
import LiveApplicationDetailPage from './pages/LiveApplicationDetailPage'
import { getBackendHealth } from './api/client'
import { startGoogleLogin } from './api/auth'
import { useSession } from './auth/useSession'
import { navigationItems, type PageId } from './types/navigation'
import './App.css'

type BackendStatus = 'checking' | 'connected' | 'disconnected'

function App() {
  const [activePage, setActivePage] = useState<PageId>('dashboard')
  const [selectedApplicationId, setSelectedApplicationId] = useState<
    string | null
  >(null)
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking')
  const session = useSession()
  const mainRef = useRef<HTMLElement>(null)
  const initialRender = useRef(true)

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

  useEffect(() => {
    const pageName =
      navigationItems.find((item) => item.id === activePage)?.label ??
      'Dashboard'

    document.title = `${pageName} | JobTrack`

    if (initialRender.current) {
      initialRender.current = false
      return
    }

    mainRef.current?.focus()
  }, [activePage, selectedApplicationId])

  function navigateTo(page: PageId) {
    setSelectedApplicationId(null)
    setActivePage(page)
  }

  function viewApplication(applicationId: string) {
    setSelectedApplicationId(applicationId)
    setActivePage('applications')
  }

  function renderPage() {
    switch (activePage) {
      case 'dashboard':
        return (
          <section className='informational-page'>
            <h2>Dashboard</h2>
            <p>
              Live dashboard summaries are coming soon. Your applications are
              available in the Applications view.
            </p>
            <button type='button' onClick={() => navigateTo('applications')}>
              View applications
            </button>
          </section>
        )
      case 'applications': {
        return selectedApplicationId ? (
          <LiveApplicationDetailPage
            applicationId={selectedApplicationId}
            onBack={() => setSelectedApplicationId(null)}
          />
        ) : (
          <LiveApplicationsPage onViewDetails={viewApplication} />
        )
      }
      case 'timeline':
        return (
          <section className='informational-page'>
            <h2>Timeline</h2>
            <p>Choose an application to view its recorded timeline.</p>
            <button type='button' onClick={() => navigateTo('applications')}>
              Browse applications
            </button>
          </section>
        )
      case 'inbox':
        return <InboxPage />
      case 'settings':
        return <SettingsPage />
    }
  }

  if (session.status === 'loading')
    return (
      <main className='auth-screen'>
        <p role='status'>Checking your session...</p>
      </main>
    )
  if (session.status === 'error')
    return (
      <main className='auth-screen'>
        <h1>JobTrack</h1>
        <p role='alert'>{session.error}</p>
        <button type='button' onClick={() => void session.refresh()}>
          Try again
        </button>
      </main>
    )
  if (session.status === 'unauthenticated')
    return (
      <main className='auth-screen'>
        <div className='auth-panel'>
          <p className='detail-eyebrow'>JOBTRACK</p>
          <h1>Keep your job search moving.</h1>
          <p>Sign in to access your applications and activity timeline.</p>
          <button type='button' onClick={startGoogleLogin}>
            Continue with Google
          </button>
        </div>
      </main>
    )

  return (
    <div className='app-layout'>
      <a className='skip-link' href='#main-content'>
        Skip to main content
      </a>
      <Sidebar activePage={activePage} onNavigate={navigateTo} />
      <div className='app-main'>
        <Header activePage={activePage} backendStatus={backendStatus} />
        <div className='session-toolbar'>
          <span>{session.user?.email}</span>
          <button type='button' onClick={() => void session.logout()}>
            Sign out
          </button>
        </div>
        <main
          id='main-content'
          ref={mainRef}
          tabIndex={-1}
          className='app-content'
        >
          {renderPage()}
        </main>
      </div>
    </div>
  )
}

export default App
