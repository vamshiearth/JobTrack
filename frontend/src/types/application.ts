import type { ActionOwner, ApplicationStage } from './dashboard'

export interface TrackedApplication {
  id: string
  companyName: string
  jobTitle: string
  location: string | null
  stage: ApplicationStage
  nextActionOwner: ActionOwner
  appliedAt: string
  lastActivityAt: string
}

export type ApplicationSort = 'last_activity_at' | 'applied_at' | 'company_name'
export type SortOrder = 'asc' | 'desc'

export interface ApplicationFilters {
  q: string
  stage: ApplicationStage | 'ALL'
  nextActionOwner: ActionOwner | 'ALL'
  sortBy: ApplicationSort
  sortOrder: SortOrder
  page: number
  pageSize: number
}
