"""FastAPI app initialization.

Assembles the application with lifespan, CORS, and the v1 API router.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.db.base import Base, engine

# Import models so they register with Base.metadata before create_all.
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup logic (create tables if missing). Shutdown is a no-op.

    Args:
        app: The FastAPI application instance (unused; required by lifespan signature).

    Yields:
        None: Control returns to the caller while the app is running.
    """
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers lifespan (create_all tables), CORS, and the v1 API router
    (health, auth, users, game sessions, admin stub).

    Returns:
        The configured FastAPI application instance.
    """
    app = FastAPI(title="Catan Backend", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    return app


def run() -> None:
    """Run the backend with uvicorn (factory mode, reload, host 0.0.0.0, port 8000)."""
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


app = create_app()
