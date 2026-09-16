"""
Backend package for the Catan app.

Exposes the FastAPI app and database models/schemas.
"""

from .main import create_app

__all__ = ['create_app']
