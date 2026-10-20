from sqlalchemy.schema import CreateIndex, CreateTable
from sqlalchemy.dialects import postgresql

from app.db.base import Base
from app.models import (
    ApplicationEvent,
    EmailMessage,
    GmailConnection,
    GmailSyncState,
    JobApplication,
    ReviewItem,
    AuthSession,
    OAuthLoginTransaction,
    User,
)


def test_all_expected_tables_are_registered():
    assert sorted(Base.metadata.tables) == [
        "application_events",
        "auth_sessions",
        "email_messages",
        "gmail_connections",
        "gmail_oauth_transactions",
        "gmail_sync_states",
        "job_applications",
        "oauth_login_transactions",
        "review_items",
        "users",
    ]


def test_each_model_has_uuid_primary_key_except_sync_state():
    for model in (
        User,
        GmailConnection,
        EmailMessage,
        JobApplication,
        ApplicationEvent,
        ReviewItem,
        AuthSession,
        OAuthLoginTransaction,
    ):
        assert [column.name for column in model.__table__.primary_key] == ["id"]
        assert str(model.id.type) == "UUID"

    assert [column.name for column in GmailSyncState.__table__.primary_key] == [
        "gmail_connection_id"
    ]


def test_foreign_keys_resolve_to_expected_tables():
    assert {fk.target_fullname for fk in EmailMessage.__table__.c.gmail_connection_id.foreign_keys} == {
        "gmail_connections.id"
    }
    assert {fk.target_fullname for fk in EmailMessage.__table__.c.job_application_id.foreign_keys} == {
        "job_applications.id"
    }
    assert {
        fk.target_fullname for fk in ApplicationEvent.__table__.c.job_application_id.foreign_keys
    } == {"job_applications.id"}
    assert {
        fk.target_fullname for fk in ReviewItem.__table__.c.suggested_application_id.foreign_keys
    } == {"job_applications.id"}


def test_duplicate_and_status_constraints_are_present():
    email_constraints = {constraint.name for constraint in EmailMessage.__table__.constraints}
    event_constraints = {constraint.name for constraint in ApplicationEvent.__table__.constraints}
    assert "email_message_identity" in email_constraints
    assert "event_idempotency" in event_constraints

    application_checks = {constraint.name for constraint in JobApplication.__table__.constraints}
    review_checks = {constraint.name for constraint in ReviewItem.__table__.constraints}
    assert "ck_job_applications_current_stage_valid" in application_checks
    assert "ck_review_items_confidence_range" in review_checks
    assert "ck_review_items_review_status_valid" in review_checks


def test_postgresql_ddl_compiles_without_database_connection():
    dialect = postgresql.dialect()
    table_sql = "\n".join(
        str(CreateTable(table).compile(dialect=dialect)) for table in Base.metadata.sorted_tables
    )
    index_sql = "\n".join(
        str(CreateIndex(index).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
        for index in table.indexes
    )

    assert 'CREATE TABLE users' in table_sql
    assert 'CREATE TABLE application_events' in table_sql
    assert 'JSONB' in table_sql
    assert 'CREATE UNIQUE INDEX uq_review_items_pending_email' in index_sql
    assert 'WHERE review_status = \'PENDING\'' in index_sql
