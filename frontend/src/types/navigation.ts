export type PageId =
  | 'dashboard'
  | 'discovery'
  | 'applications'
  | 'timeline'
  | 'inbox'
  | 'reviews'
  | 'queue'
  | 'settings'

export interface NavigationItem {
  id: PageId
  label: string
  icon: string
}

export const navigationItems: NavigationItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '◫' },
  { id: 'discovery', label: 'Discovery', icon: '⌕' },
  { id: 'applications', label: 'Applications', icon: '▣' },
  { id: 'timeline', label: 'Timeline', icon: '▤' },
  { id: 'inbox', label: 'Email Inbox', icon: '✉' },
  { id: 'reviews', label: 'Recruitment Reviews', icon: '✓' },
  { id: 'queue', label: 'Application Queue', icon: '→' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
]
