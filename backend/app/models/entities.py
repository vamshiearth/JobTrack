import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


Timestamp = DateTime(timezone=True)


def uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def timestamp_column() -> Mapped[datetime]:
    return mapped_column(Timestamp, nullable=False, server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email_lower", text("lower(email)"), unique=True),)

    id: Mapped[uuid.UUID] = uuid_column()
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    google_sub: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    gmail_connections: Mapped[list["GmailConnection"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["JobApplication"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    review_items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    candidate_profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class GmailConnection(Base):
    __tablename__ = "gmail_connections"
    __table_args__ = (
        CheckConstraint(
            "connection_status IN ('CONNECTED', 'RECONNECT_REQUIRED', 'DISCONNECTED')",
            name="connection_status_valid",
        ),
        Index("ix_gmail_connections_user_id", "user_id"),
        Index(
            "uq_gmail_connections_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("connection_status <> 'DISCONNECTED'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    google_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    email_address: Mapped[str] = mapped_column(String(320), nullable=False)
    encrypted_refresh_token: Mapped[bytes | None] = mapped_column(LargeBinary)
    granted_scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()
    disconnected_at: Mapped[datetime | None] = mapped_column(Timestamp)

    user: Mapped[User] = relationship(back_populates="gmail_connections")
    sync_state: Mapped["GmailSyncState | None"] = relationship(
        back_populates="gmail_connection", uselist=False, cascade="all, delete-orphan"
    )
    email_messages: Mapped[list["EmailMessage"]] = relationship(
        back_populates="gmail_connection"
    )


class GmailSyncState(Base):
    __tablename__ = "gmail_sync_states"
    __table_args__ = (
        CheckConstraint("sync_status IN ('IDLE', 'RUNNING', 'FAILED')", name="sync_status_valid"),
    )

    gmail_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gmail_connections.id", ondelete="CASCADE"), primary_key=True
    )
    last_history_id: Mapped[str | None] = mapped_column(String(64))
    sync_status: Mapped[str] = mapped_column(String(20), nullable=False)
    backfill_after: Mapped[datetime | None] = mapped_column(Timestamp)
    last_attempt_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_error_message: Mapped[str | None] = mapped_column(Text)

    gmail_connection: Mapped[GmailConnection] = relationship(back_populates="sync_state")


class EmailMessage(Base):
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint("gmail_connection_id", "gmail_message_id", name="email_message_identity"),
        Index("ix_email_messages_gmail_connection_id", "gmail_connection_id"),
        Index("ix_email_messages_job_application_id", "job_application_id"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    gmail_connection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gmail_connections.id"), nullable=False
    )
    gmail_message_id: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_thread_id: Mapped[str] = mapped_column(String(255), nullable=False)
    job_application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_applications.id", ondelete="SET NULL")
    )
    sender_address: Mapped[str | None] = mapped_column(String(320))
    subject: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    classification_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(Timestamp)
    created_at: Mapped[datetime] = timestamp_column()

    gmail_connection: Mapped[GmailConnection] = relationship(back_populates="email_messages")
    job_application: Mapped["JobApplication | None"] = relationship(back_populates="email_messages")
    source_events: Mapped[list["ApplicationEvent"]] = relationship(back_populates="source_email")
    review_items: Mapped[list["ReviewItem"]] = relationship(back_populates="email_message")


class JobApplication(Base):
    __tablename__ = "job_applications"
    __table_args__ = (
        CheckConstraint(
            "application_source IN ('MANUAL', 'EMAIL')", name="application_source_valid"
        ),
        CheckConstraint(
            "current_stage IN ('APPLIED', 'SCREENING', 'ASSESSMENT', 'INTERVIEW', 'OFFER', 'REJECTED', 'WITHDRAWN')",
            name="current_stage_valid",
        ),
        CheckConstraint(
            "next_action_owner IN ('USER', 'EMPLOYER', 'NONE')", name="next_action_owner_valid"
        ),
        Index("ix_job_applications_user_id", "user_id"),
        Index("ix_job_applications_applied_at", "applied_at"),
        Index("ix_job_applications_current_stage", "current_stage"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_url: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    applied_at: Mapped[date | None] = mapped_column(Date)
    application_source: Mapped[str] = mapped_column(String(20), nullable=False)
    current_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    next_action_owner: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    last_activity_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    user: Mapped[User] = relationship(back_populates="applications")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="job_application", cascade="all, delete-orphan"
    )
    email_messages: Mapped[list[EmailMessage]] = relationship(back_populates="job_application")
    review_items: Mapped[list["ReviewItem"]] = relationship(
        back_populates="suggested_application"
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"
    __table_args__ = (
        CheckConstraint(
            "event_kind IN ('APPLICATION_SUBMITTED', 'RECRUITER_CONTACTED', 'ASSESSMENT_INVITED', 'ASSESSMENT_COMPLETED', 'INTERVIEW_SCHEDULED', 'INTERVIEW_COMPLETED', 'OFFER_RECEIVED', 'REJECTION_RECEIVED', 'APPLICATION_WITHDRAWN', 'MANUAL_CORRECTION')",
            name="event_kind_valid",
        ),
        CheckConstraint("interview_round IS NULL OR interview_round > 0", name="interview_round_positive"),
        CheckConstraint("origin IN ('MANUAL', 'GMAIL', 'SYSTEM')", name="origin_valid"),
        UniqueConstraint("job_application_id", "idempotency_key", name="event_idempotency"),
        Index("ix_application_events_job_application_id", "job_application_id"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    job_application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False
    )
    source_email_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("email_messages.id")
    )
    event_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    interview_round: Mapped[int | None] = mapped_column(Integer)
    origin: Mapped[str] = mapped_column(String(20), nullable=False)
    verified_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    recorded_at: Mapped[datetime] = timestamp_column()

    job_application: Mapped[JobApplication] = relationship(back_populates="events")
    source_email: Mapped[EmailMessage | None] = relationship(back_populates="source_events")


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "review_status IN ('PENDING', 'APPROVED', 'DISMISSED')", name="review_status_valid"
        ),
        Index("ix_review_items_user_id", "user_id"),
        Index(
            "uq_review_items_pending_email",
            "email_message_id",
            unique=True,
            postgresql_where=text("review_status = 'PENDING'"),
        ),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    email_message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("email_messages.id"), nullable=False
    )
    suggested_application_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_applications.id")
    )
    suggested_event_kind: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()
    resolved_at: Mapped[datetime | None] = mapped_column(Timestamp)

    user: Mapped[User] = relationship(back_populates="review_items")
    email_message: Mapped[EmailMessage] = relationship(back_populates="review_items")
    suggested_application: Mapped[JobApplication | None] = relationship(
        back_populates="review_items"
    )


class JobOpportunity(Base):
    __tablename__ = "job_opportunities"
    __table_args__ = (
        CheckConstraint("status IN ('SAVED', 'ARCHIVED')", name="job_opportunity_status_valid"),
        CheckConstraint("source_type = 'MANUAL'", name="job_opportunity_source_type_valid"),
        UniqueConstraint("user_id", "normalized_url", name="job_opportunity_user_url_unique"),
        Index("ix_job_opportunities_user_id", "user_id"),
        Index("ix_job_opportunities_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, default="MANUAL")
    source_job_id: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))
    work_arrangement: Mapped[str | None] = mapped_column(String(30))
    employment_type: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SAVED")
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    user: Mapped[User] = relationship()
    preparations: Mapped[list["ApplicationPreparation"]] = relationship(
        back_populates="opportunity", cascade="all, delete-orphan"
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    experience_summary: Mapped[str | None] = mapped_column(Text)
    target_roles: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    preferred_locations: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    remote_preference: Mapped[str | None] = mapped_column(String(20))
    resume_version: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    user: Mapped[User] = relationship(back_populates="candidate_profile")
    assessments: Mapped[list["JobMatchAssessment"]] = relationship(
        back_populates="candidate_profile", cascade="all, delete-orphan"
    )


class JobMatchAssessment(Base):
    __tablename__ = "job_match_assessments"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "candidate_profile_id", "profile_revision",
            name="job_match_assessment_revision_unique",
        ),
        Index("ix_job_match_assessments_opportunity_id", "opportunity_id"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_opportunities.id", ondelete="CASCADE"), nullable=False
    )
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False
    )
    profile_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    opportunity_updated_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    scoring_model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int | None] = mapped_column(Integer)
    evidence_coverage: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    matched_skills: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    unverified_requirements: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    explanations: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    eligibility_status: Mapped[str] = mapped_column(String(30), nullable=False)
    ranking_status: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = timestamp_column()

    opportunity: Mapped[JobOpportunity] = relationship()
    candidate_profile: Mapped[CandidateProfile] = relationship(back_populates="assessments")


class ApplicationPreparation(Base):
    __tablename__ = "application_preparations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'NEEDS_REVIEW', 'APPROVED', 'STALE', 'ARCHIVED')",
            name="application_preparation_status_valid",
        ),
        Index("ix_application_preparations_user_id", "user_id"),
        Index("ix_application_preparations_opportunity_id", "opportunity_id"),
    )

    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("job_opportunities.id", ondelete="CASCADE"), nullable=False)
    candidate_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    match_assessment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("job_match_assessments.id", ondelete="SET NULL"))
    source_fingerprint: Mapped[str] = mapped_column(String(255), nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    resume_suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    application_answers: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    review_notes: Mapped[str | None] = mapped_column(Text)
    approved_at: Mapped[datetime | None] = mapped_column(Timestamp)
    approved_revision: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column()

    user: Mapped[User] = relationship()
    opportunity: Mapped[JobOpportunity] = relationship(back_populates="preparations")
    candidate_profile: Mapped[CandidateProfile] = relationship()
    match_assessment: Mapped[JobMatchAssessment | None] = relationship()
