"""Shared pytest setup for the backend test suite."""

from __future__ import annotations

import os

# importing `app` builds the SQLAlchemy engine at import time, which requires a
# database url. set a placeholder before any test module imports the package;
# create_engine does not open a connection until it is used.
os.environ.setdefault('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
