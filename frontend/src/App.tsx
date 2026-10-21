import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import InboxPage from './pages/InboxPage'
import SettingsPage from './pages/SettingsPage'
import LiveApplicationsPage from './pages/LiveApplicationsPage'
import LiveApplicationDetailPage from './pages/LiveApplicationDetailPage'
import LiveDashboardPage from './pages/LiveDashboardPage'
import LiveTimelinePage from './pages/LiveTimelinePage'
import AddApplicationForm from './components/applications/AddApplicationForm'
import ReviewQueuePage from './pages/ReviewQueuePage'
import ApplicationQueuePage from './pages/ApplicationQueuePage'
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
  const [isAddingApplication, setIsAddingApplication] = useState(false)
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
    setIsAddingApplication(false)
    setSelectedApplicationId(null)
    setActivePage(page)
  }

  function viewApplication(applicationId: string) {
    setIsAddingApplication(false)
    setSelectedApplicationId(applicationId)
    setActivePage('applications')
  }

  function openAddApplication() {
    setSelectedApplicationId(null)
    setIsAddingApplication(true)
    setActivePage('applications')
  }

  function renderPage() {
    switch (activePage) {
      case 'dashboard':
        return (
          <LiveDashboardPage
            onViewApplication={viewApplication}
            onViewApplications={() => navigateTo('applications')}
          />
        )
      case 'applications': {
        if (isAddingApplication) {
          return (
            <section className='applications-page'>
              <div className='applications-intro'>
                <div>
                  <h2>Add Job Application</h2>
                  <p>Save an application to your account.</p>
                </div>
              </div>
              <div className='applications-panel'>
                <AddApplicationForm
                  csrfToken={session.user!.csrf_token}
                  onCancel={() => setIsAddingApplication(false)}
                  onCreated={viewApplication}
                />
              </div>
            </section>
          )
        }
        return selectedApplicationId ? (
          <LiveApplicationDetailPage
            applicationId={selectedApplicationId}
            csrfToken={session.user!.csrf_token}
            onBack={() => setSelectedApplicationId(null)}
            onDeleted={() => {
              setSelectedApplicationId(null)
              setIsAddingApplication(false)
              setActivePage('applications')
            }}
          />
        ) : (
          <LiveApplicationsPage
            onViewDetails={viewApplication}
            onAddApplication={openAddApplication}
          />
        )
      }
      case 'timeline':
        return <LiveTimelinePage onViewApplication={viewApplication} />
      case 'inbox':
        return <InboxPage />
      case 'reviews':
        return (
          <ReviewQueuePage
            csrfToken={session.user!.csrf_token}
            onViewApplication={viewApplication}
          />
        )
      case 'queue':
        return (
          <ApplicationQueuePage
            csrfToken={session.user!.csrf_token}
            onViewApplication={viewApplication}
          />
        )
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
