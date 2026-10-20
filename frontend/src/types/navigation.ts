export type PageId =
  | 'dashboard'
  | 'applications'
  | 'timeline'
  | 'inbox'
  | 'settings'

export interface NavigationItem {
  id: PageId
  label: string
  icon: string
}

export const navigationItems: NavigationItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '◫' },
  { id: 'applications', label: 'Applications', icon: '▣' },
  { id: 'timeline', label: 'Timeline', icon: '▤' },
  { id: 'inbox', label: 'Email Inbox', icon: '✉' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
]
