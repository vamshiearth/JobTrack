from sqlalchemy import inspect, text

from app.db.session import engine


EXPECTED_TABLES = {
    "users",
    "gmail_connections",
    "gmail_sync_states",
    "email_messages",
    "job_applications",
    "application_events",
    "review_items",
}


def test_application_tables_exist():
    inspector = inspect(engine)
    actual_tables = set(inspector.get_table_names(schema="public"))

    assert EXPECTED_TABLES.issubset(actual_tables)


def test_database_connection_is_not_superuser():
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT rolsuper, rolcreatedb, rolcreaterole
                FROM pg_roles
                WHERE rolname = current_user
                """
            )
        ).one()

    assert result == (False, False, False)


def test_application_tables_have_primary_keys():
    inspector = inspect(engine)

    for table_name in EXPECTED_TABLES:
        assert inspector.get_pk_constraint(table_name, schema="public")["constrained_columns"]


def test_application_tables_have_foreign_keys():
    inspector = inspect(engine)
    foreign_key_tables = {
        table_name
        for table_name in EXPECTED_TABLES
        if inspector.get_foreign_keys(table_name, schema="public")
    }

    assert foreign_key_tables == {
        "gmail_connections",
        "gmail_sync_states",
        "email_messages",
        "job_applications",
        "application_events",
        "review_items",
    }


def test_required_unique_and_check_constraints_exist():
    inspector = inspect(engine)
    constraints = {
        constraint["name"]
        for table_name in EXPECTED_TABLES
        for constraint in inspector.get_unique_constraints(table_name, schema="public")
    }
    constraints.update(
        constraint["name"]
        for table_name in EXPECTED_TABLES
        for constraint in inspector.get_check_constraints(table_name, schema="public")
    )

    assert {
        "email_message_identity",
        "event_idempotency",
        "ck_job_applications_current_stage_valid",
        "ck_review_items_confidence_range",
    }.issubset(constraints)