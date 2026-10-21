from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine


def test_database_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_database_identity():
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    current_schema()
                """
            )
        ).one()

    settings = get_settings()
    assert result[0] == settings.db_name
    assert result[1] == settings.db_user
    assert result[2] == "public"


def test_database_user_is_not_superuser():
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
