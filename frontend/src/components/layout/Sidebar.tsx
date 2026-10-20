import { navigationItems, type PageId } from '../../types/navigation'

interface SidebarProps {
  activePage: PageId
  onNavigate: (page: PageId) => void
}

export default function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <aside className='sidebar'>
      <div className='sidebar-brand'>
        <div className='brand-icon'>JT</div>
        <div>
          <strong>JobTrack</strong>
          <span>Application Manager</span>
        </div>
      </div>
      <nav className='sidebar-nav' aria-label='Main navigation'>
        {navigationItems.map((item) => (
          <button
            key={item.id}
            type='button'
            className={`nav-item ${activePage === item.id ? 'active' : ''}`}
            aria-current={activePage === item.id ? 'page' : undefined}
            onClick={() => onNavigate(item.id)}
          >
            <span className='nav-icon' aria-hidden='true'>
              {item.icon}
            </span>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className='sidebar-footer'>
        <span>JobTrack v0.1.0</span>
        <small>Development environment</small>
      </div>
    </aside>
  )
}
