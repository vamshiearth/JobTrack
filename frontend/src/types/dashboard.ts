export type ApplicationStage =
  | 'APPLIED'
  | 'SCREENING'
  | 'ASSESSMENT'
  | 'INTERVIEW'
  | 'OFFER'
  | 'REJECTED'
  | 'WITHDRAWN'

export type ActionOwner = 'USER' | 'EMPLOYER' | 'NONE'

export interface DashboardStats {
  totalApplications: number
  waitingForEmployer: number
  pendingAssessments: number
  upcomingInterviews: number
}

export interface RecentApplication {
  id: string
  company: string
  jobTitle: string
  stage: ApplicationStage
  nextActionOwner: ActionOwner
  lastActivity: string
}

export interface UpcomingAction {
  id: string
  applicationId: string
  company: string
  title: string
  type: 'ASSESSMENT' | 'INTERVIEW' | 'FOLLOW_UP'
  dueDate: string | null
}
