import {
  getApplicationEvents,
  getApplications,
  type ApiApplication,
  type ApiTimelineEvent,
  type ApplicationQuery,
} from './applications'
import type { ApplicationStage } from '../types/dashboard'

export interface LiveDashboardData {
  totalApplications: number
  interviewCount: number
  assessmentCount: number
  offerCount: number
  recentApplications: ApiApplication[]
  userActions: ApiApplication[]
  totalUserActions: number
}

export interface LiveActivity {
  application: ApiApplication
  event: ApiTimelineEvent
}

export interface LiveTimelineData {
  activities: LiveActivity[]
  sampledApplications: number
  totalApplications: number
}

function query(changes: Partial<ApplicationQuery> = {}): ApplicationQuery {
  return {
    q: '',
    stage: 'ALL',
    nextActionOwner: 'ALL',
    page: 1,
    pageSize: 10,
    sortBy: 'last_activity_at',
    sortOrder: 'desc',
    ...changes,
  }
}

async function stageCount(stage: ApplicationStage) {
  const result = await getApplications(query({ stage, pageSize: 1 }))
  return result.total
}

export async function loadDashboard(): Promise<LiveDashboardData> {
  const [recent, interviews, assessments, offers, actionQueue] =
    await Promise.all([
      getApplications(query({ pageSize: 5 })),
      stageCount('INTERVIEW'),
      stageCount('ASSESSMENT'),
      stageCount('OFFER'),
      getApplications(query({ nextActionOwner: 'USER', pageSize: 10 })),
    ])

  return {
    totalApplications: recent.total,
    interviewCount: interviews,
    assessmentCount: assessments,
    offerCount: offers,
    recentApplications: recent.items,
    userActions: actionQueue.items,
    totalUserActions: actionQueue.total,
  }
}

export async function loadTimeline(): Promise<LiveTimelineData> {
  const recent = await getApplications(query({ pageSize: 10 }))
  const timelines = await Promise.all(
    recent.items.map(async (application) => {
      const response = await getApplicationEvents(application.id)
      return response.items.map(
        (event): LiveActivity => ({ application, event }),
      )
    }),
  )
  const activities = timelines
    .flat()
    .sort(
      (a, b) =>
        b.event.occurred_at.localeCompare(a.event.occurred_at) ||
        a.event.id.localeCompare(b.event.id),
    )

  return {
    activities,
    sampledApplications: recent.items.length,
    totalApplications: recent.total,
  }
}