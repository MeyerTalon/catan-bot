"""SQLAlchemy declarative base and engine."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

Base = declarative_base()


def _get_engine() -> Engine:
    """Build the SQLAlchemy engine from settings.

    Returns:
        Engine configured with settings.database_url and future=True.
    """
    settings = get_settings()
    return create_engine(settings.database_url, future=True)


engine = _get_engine()
