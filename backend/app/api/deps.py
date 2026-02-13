"""API-specific dependencies (e.g. get_db, get_current_user)."""

from __future__ import annotations

from typing import Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_user_id_from_token
from app.db.session import db_session
from app.models.user import User


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped database session.

    Yields:
        Session: A SQLAlchemy session. Commits on success, rolls back on exception.
    """
    with db_session() as session:
        yield session


def get_current_user_id(authorization: str = Header(..., alias="Authorization")) -> str:
    """Extract and validate user ID from Authorization header.

    Args:
        authorization: Authorization header (format: "Bearer <token>")

    Returns:
        User ID (UUID as string) from the validated token.

    Raises:
        HTTPException: 401 if Authorization header is missing, malformed, or token is invalid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
        )
    token = authorization.replace("Bearer ", "", 1).strip()
    return get_user_id_from_token(token)


def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from the database.

    Args:
        user_id: User ID extracted from JWT token.
        db: Database session.

    Returns:
        User model instance for the authenticated user.

    Raises:
        HTTPException: 404 if user not found in database.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please create a user profile first.",
        )
    return user
