import type {
  DashboardStats,
  RecentApplication,
  UpcomingAction,
} from '../types/dashboard'

export const mockStats: DashboardStats = {
  totalApplications: 24,
  waitingForEmployer: 14,
  pendingAssessments: 3,
  upcomingInterviews: 2,
}

export const mockRecentApplications: RecentApplication[] = [
  {
    id: 'demo-1',
    company: 'Example Technologies',
    jobTitle: 'Oracle CPQ Developer',
    stage: 'ASSESSMENT',
    nextActionOwner: 'USER',
    lastActivity: '2026-10-19',
  },
  {
    id: 'demo-2',
    company: 'Nova Systems',
    jobTitle: 'Java Software Engineer',
    stage: 'APPLIED',
    nextActionOwner: 'EMPLOYER',
    lastActivity: '2026-10-18',
  },
  {
    id: 'demo-3',
    company: 'Cloudworks',
    jobTitle: 'Backend Developer',
    stage: 'INTERVIEW',
    nextActionOwner: 'USER',
    lastActivity: '2026-10-17',
  },
  {
    id: 'demo-4',
    company: 'Atlas Digital',
    jobTitle: 'CPQ Integration Developer',
    stage: 'SCREENING',
    nextActionOwner: 'EMPLOYER',
    lastActivity: '2026-10-16',
  },
]

export const mockUpcomingActions: UpcomingAction[] = [
  {
    id: 'action-1',
    applicationId: 'demo-1',
    company: 'Example Technologies',
    title: 'Complete coding assessment',
    type: 'ASSESSMENT',
    dueDate: null,
  },
  {
    id: 'action-2',
    applicationId: 'demo-3',
    company: 'Cloudworks',
    title: 'Prepare for interview',
    type: 'INTERVIEW',
    dueDate: null,
  },
]
