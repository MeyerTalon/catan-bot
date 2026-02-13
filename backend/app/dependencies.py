"""Shared dependencies (re-export API deps for convenience)."""

from app.api.deps import get_db

__all__ = ["get_db"]
