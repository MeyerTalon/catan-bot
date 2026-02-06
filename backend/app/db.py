"""SQLAlchemy engine, base, and session utilities.

Provides Base for ORM models, a shared engine, SessionLocal, and db_session()
for request-scoped transactional access to the database.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

from .config import get_settings


Base = declarative_base()


def _get_engine() -> Engine:
    """Build the SQLAlchemy engine from settings.

    Returns:
        Engine configured with settings.database_url and future=True.
    """
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


engine = _get_engine()
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

