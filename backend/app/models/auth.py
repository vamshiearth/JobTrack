import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


Timestamp = DateTime(timezone=True)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_auth_sessions_token_hash"),
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(Timestamp)


class OAuthLoginTransaction(Base):
    __tablename__ = "oauth_login_transactions"
    __table_args__ = (
        UniqueConstraint("state_hash", name="uq_oauth_login_transactions_state_hash"),
        Index("ix_oauth_login_transactions_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    nonce: Mapped[str] = mapped_column(String(255), nullable=False)
    pkce_code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False, server_default=func.now())
    consumed_at: Mapped[datetime | None] = mapped_column(Timestamp)


class GmailOAuthTransaction(Base):
    __tablename__ = "gmail_oauth_transactions"
    __table_args__ = (
        UniqueConstraint("state_hash", name="uq_gmail_oauth_transactions_state_hash"),
        Index("ix_gmail_oauth_transactions_expires_at", "expires_at"),
        Index("ix_gmail_oauth_transactions_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    auth_session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("auth_sessions.id"), nullable=False)
    state_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    nonce: Mapped[str] = mapped_column(String(255), nullable=False)
    pkce_code_verifier: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False)
    created_at: Mapped[datetime] = mapped_column(Timestamp, nullable=False, server_default=func.now())
    consumed_at: Mapped[datetime | None] = mapped_column(Timestamp)