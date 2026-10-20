export type TimelineEventKind =
  | 'APPLICATION_SUBMITTED'
  | 'RECRUITER_CONTACTED'
  | 'ASSESSMENT_INVITED'
  | 'ASSESSMENT_COMPLETED'
  | 'INTERVIEW_SCHEDULED'
  | 'INTERVIEW_COMPLETED'
  | 'OFFER_RECEIVED'
  | 'REJECTION_RECEIVED'
  | 'APPLICATION_WITHDRAWN'

export interface TimelineEvent {
  id: string
  applicationId: string
  kind: TimelineEventKind
  occurredAt: string
  interviewRound: number | null
  note: string | null
}
