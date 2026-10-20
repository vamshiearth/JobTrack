import RecentApplications from '../components/dashboard/RecentApplications'
import StatCard from '../components/dashboard/StatCard'
import UpcomingActions from '../components/dashboard/UpcomingActions'
import {
  mockRecentApplications,
  mockStats,
  mockUpcomingActions,
} from '../data/mockDashboard'

interface DashboardPageProps {
  onViewApplications: () => void
}

export default function DashboardPage({
  onViewApplications,
}: DashboardPageProps) {
  return (
    <section className='dashboard-page'>
      <div className='dashboard-intro'>
        <div>
          <h2>Application Overview</h2>
          <p>Stay on top of your job search.</p>
        </div>
        <span className='demo-label'>Demo data - Gmail not connected</span>
      </div>
      <div className='stats-grid'>
        <StatCard
          title='Total Applications'
          value={mockStats.totalApplications}
          icon='▣'
          description='Applications tracked'
        />
        <StatCard
          title='Waiting for Reply'
          value={mockStats.waitingForEmployer}
          icon='◷'
          description='Awaiting employer action'
        />
        <StatCard
          title='Assessments Pending'
          value={mockStats.pendingAssessments}
          icon='✎'
          description='Assessments to complete'
        />
        <StatCard
          title='Upcoming Interviews'
          value={mockStats.upcomingInterviews}
          icon='▤'
          description='Interview preparation'
        />
      </div>
      <div className='dashboard-content-grid'>
        <RecentApplications
          applications={mockRecentApplications}
          onViewAll={onViewApplications}
        />
        <UpcomingActions actions={mockUpcomingActions} />
      </div>
    </section>
  )
}
