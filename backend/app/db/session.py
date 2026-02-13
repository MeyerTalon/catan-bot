"""Database session factory and context manager."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import sessionmaker, Session

from app.db.base import engine

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Yields a Session that commits on normal exit and rolls back on exception.
    The session is always closed when the block exits.

    Yields:
        Session: A SQLAlchemy session for the scope of the with block.

    Raises:
        Exception: Re-raises any exception after rolling back the transaction.
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
