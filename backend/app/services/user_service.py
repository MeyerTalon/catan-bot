"""User service: read user profiles (rows are created by the auth flow)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.user import user_crud
from app.schemas.user import UserRead


def get_user(db: Session, user_id: str) -> UserRead:
    """Get a user by UUID.

    Args:
        db: Database session.
        user_id: User UUID as string.

    Returns:
        User profile as UserRead schema.

    Raises:
        HTTPException: 404 if user not found.
    """
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Not found')
    return UserRead.model_validate(user)


class UserService:
    """User profile service for retrieving user records linked to Cognito users."""

    get_user = staticmethod(get_user)


user_service = UserService()
