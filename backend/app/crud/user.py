"""User CRUD operations."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: uuid.UUID | str) -> Optional[User]:
    """Get a user by primary key.

    Args:
        db: Database session.
        user_id: User UUID as UUID object or string.

    Returns:
        User model instance if found, None otherwise.
    """
    return db.get(User, str(user_id) if isinstance(user_id, str) else user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email.

    Args:
        db: Database session.
        email: User email address.

    Returns:
        User model instance if found, None otherwise.
    """
    return db.query(User).filter(User.email == email).first()


def create(db: Session, *, id: uuid.UUID, email: str) -> User:
    """Create a user.

    Args:
        db: Database session.
        id: User UUID (must match Supabase auth user id).
        email: User email address.

    Returns:
        Created User model instance.

    Note:
        Caller must commit or use within db_session context manager.
    """
    user = User(id=id, email=email)
    db.add(user)
    db.flush()
    return user


# Expose a simple namespace for endpoints that want to use crud
class UserCRUD:
    """User CRUD operations namespace.

    Provides database operations for User model: get by id, get by email, and create.
    """

    get = staticmethod(get_by_id)
    get_by_email = staticmethod(get_by_email)
    create = staticmethod(create)


user_crud = UserCRUD()
