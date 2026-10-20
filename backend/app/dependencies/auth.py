from uuid import UUID

from fastapi import HTTPException, status


def get_current_user_id() -> UUID:
    """Deny requests until a production authentication mechanism is installed."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )