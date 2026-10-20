from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine


def main() -> None:
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        current_database() AS database_name,
                        current_user AS database_user,
                        current_schema() AS schema_name,
                        version() AS server_version
                    """
                )
            ).mappings().one()
            print("Database connection: SUCCESS")
            print(f"Database: {result['database_name']}")
            print(f"User: {result['database_user']}")
            print(f"Schema: {result['schema_name']}")
            print(f"Server: {result['server_version'].split(',')[0]}")
    except SQLAlchemyError:
        print("Database connection: FAILED")
        print("Check PostgreSQL service, host, port, database name and credentials.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
