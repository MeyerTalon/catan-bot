"""API-specific dependencies (e.g. get_db)."""

from __future__ import annotations

from typing import Generator

from sqlalchemy.orm import Session

from app.db.session import db_session


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped database session.

    Yields:
        Session: A SQLAlchemy session. Commits on success, rolls back on exception.
    """
    with db_session() as session:
        yield session
