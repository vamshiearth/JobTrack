import { useEffect, useRef, useState } from 'react'
import Sidebar from './components/layout/Sidebar'
import Header from './components/layout/Header'
import ApplicationsPage from './pages/ApplicationsPage'
import ApplicationDetailPage from './pages/ApplicationDetailPage'
import DashboardPage from './pages/DashboardPage'
import InboxPage from './pages/InboxPage'
import SettingsPage from './pages/SettingsPage'
import TimelinePage from './pages/TimelinePage'
import { mockApplications } from './data/mockApplications'
import { getBackendHealth } from './api/client'
import { navigationItems, type PageId } from './types/navigation'
import './App.css'

type BackendStatus = 'checking' | 'connected' | 'disconnected'

function App() {
  const [activePage, setActivePage] = useState<PageId>('dashboard')
  const [selectedApplicationId, setSelectedApplicationId] = useState<
    string | null
  >(null)
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking')
  const mainRef = useRef<HTMLElement>(null)
  const initialRender = useRef(true)

  const selectedApplication = selectedApplicationId
    ? mockApplications.find(
        (application) => application.id === selectedApplicationId,
      )
    : undefined

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
    const pageName = selectedApplication
      ? selectedApplication.jobTitle
      : (navigationItems.find((item) => item.id === activePage)?.label ??
        'Dashboard')

    document.title = `${pageName} | JobTrack`

    if (initialRender.current) {
      initialRender.current = false
      return
    }

    mainRef.current?.focus()
  }, [activePage, selectedApplicationId, selectedApplication])

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
          <DashboardPage
            onViewApplications={() => navigateTo('applications')}
          />
        )
      case 'applications': {
        if (selectedApplication) {
          return (
            <ApplicationDetailPage
              application={selectedApplication}
              onBack={() => setSelectedApplicationId(null)}
            />
          )
        }

        return <ApplicationsPage onViewDetails={viewApplication} />
      }
      case 'timeline':
        return <TimelinePage onViewApplication={viewApplication} />
      case 'inbox':
        return <InboxPage />
      case 'settings':
        return <SettingsPage />
    }
  }

  return (
    <div className='app-layout'>
      <a className='skip-link' href='#main-content'>
        Skip to main content
      </a>
      <Sidebar activePage={activePage} onNavigate={navigateTo} />
      <div className='app-main'>
        <Header activePage={activePage} backendStatus={backendStatus} />
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
