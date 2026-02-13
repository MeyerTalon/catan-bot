"""Base model class; re-exports declarative Base from db."""

from app.db.base import Base

__all__ = ["Base"]
