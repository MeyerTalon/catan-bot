"""User CRUD operations."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User


def get_by_id(db: Session, user_id: uuid.UUID | str) -> Optional[User]:
    """Get a user by primary key."""
    return db.get(User, str(user_id) if isinstance(user_id, str) else user_id)


def get_by_email(db: Session, email: str) -> Optional[User]:
    """Get a user by email."""
    return db.query(User).filter(User.email == email).first()


def create(db: Session, *, id: uuid.UUID, email: str) -> User:
    """Create a user. Caller must commit or use within db_session."""
    user = User(id=id, email=email)
    db.add(user)
    db.flush()
    return user


# Expose a simple namespace for endpoints that want to use crud
class UserCRUD:
    get = staticmethod(get_by_id)
    get_by_email = staticmethod(get_by_email)
    create = staticmethod(create)


user_crud = UserCRUD()
