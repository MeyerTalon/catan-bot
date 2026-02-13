"""User service: create and get user profiles."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.user import user_crud
from app.models.user import User
from app.schemas.user import UserCreate, UserRead


def create_user(db: Session, payload: UserCreate) -> UserRead:
    """Create a user profile.

    Args:
        db: Database session.
        payload: User creation data containing id (UUID) and email.

    Returns:
        Created user profile as UserRead schema.

    Raises:
        HTTPException: 400 if id or email already exists.
    """
    existing = user_crud.get(db, payload.id) or user_crud.get_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )
    user = user_crud.create(db, id=payload.id, email=payload.email)
    return UserRead.model_validate(user)


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return UserRead.model_validate(user)


class UserService:
    """User profile service for creating and retrieving user records.

    Provides business logic for user profile management linked to Supabase auth users.
    """

    create_user = staticmethod(create_user)
    get_user = staticmethod(get_user)


user_service = UserService()
