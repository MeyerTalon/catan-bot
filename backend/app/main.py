"""FastAPI app initialization.

Assembles the application with lifespan, optional CORS, a request body cap,
and the v1 API router.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import models as _models  # noqa: F401  # register metadata for alembic
from app.api.v1.api import api_router
from app.core.config import get_settings

# larger than any legitimate request (a game state is capped at 64 KB) and
# small enough that a flood of bodies cannot exhaust the task's memory
MAX_BODY_BYTES = 1024 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Yield while the app is running.

    Schema changes are applied with Alembic (`db/`), not create_all.

    Args:
        app: The FastAPI application instance (unused; required by lifespan signature).

    Yields:
        None: Control returns to the caller while the app is running.
    """
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Registers lifespan, CORS (only for the origins in CORS_ALLOWED_ORIGINS; in
    production the api is same-origin behind CloudFront and needs none), a
    request body size cap, and the v1 API router (health, auth, users, game
    sessions). The OpenAPI schema at /openapi.json is the source of truth for
    frontend wire types.

    Returns:
        The configured FastAPI application instance.
    """
    settings = get_settings()
    app = FastAPI(title='Catan Backend', version='0.1.0', lifespan=lifespan)

    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
            allow_headers=['Authorization', 'Content-Type'],
        )

    @app.middleware('http')
    async def limit_body_size(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Reject requests that declare a body larger than MAX_BODY_BYTES.

        Args:
            request: Incoming request.
            call_next: Next handler in the middleware chain.

        Returns:
            413 when the declared Content-Length is too large, else the downstream response.
        """
        length = request.headers.get('content-length')
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={'detail': 'Request body too large.'},
            )
        return await call_next(request)

    app.include_router(api_router)

    return app


def run() -> None:
    """Run the backend with uvicorn (factory mode, reload, host 0.0.0.0, port 8000)."""
    uvicorn.run(
        'app.main:create_app',
        factory=True,
        host='0.0.0.0',
        port=8000,
        reload=True,
    )


app = create_app()
