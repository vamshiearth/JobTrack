from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User


class AccountLinkingRequired(Exception):
    pass


def resolve_google_user(
    db: Session,
    *,
    subject: str,
    email: str,
    display_name: str,
) -> User:
    existing = db.scalar(select(User).where(User.google_sub == subject))
    if existing is not None:
        return existing

    email_owner = db.scalar(select(User).where(User.email == email))
    if email_owner is not None:
        raise AccountLinkingRequired()

    user = User(google_sub=subject, email=email, display_name=display_name or email)
    db.add(user)
    db.flush()
    return user