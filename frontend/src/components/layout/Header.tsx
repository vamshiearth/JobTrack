import { navigationItems, type PageId } from '../../types/navigation'

interface HeaderProps {
  activePage: PageId
  backendStatus: 'checking' | 'connected' | 'disconnected'
}

export default function Header({ activePage, backendStatus }: HeaderProps) {
  const page = navigationItems.find((item) => item.id === activePage)
  const statusLabel = {
    checking: 'Checking backend',
    connected: 'Backend connected',
    disconnected: 'Backend unavailable',
  }[backendStatus]

  return (
    <header className='app-header'>
      <div>
        <h1>{page?.label ?? 'JobTrack'}</h1>
        <p>Manage your job search in one place.</p>
      </div>
      <div className='connection-badge' role='status'>
        <span className={`connection-dot ${backendStatus}`} />
        {statusLabel}
      </div>
    </header>
  )
}
