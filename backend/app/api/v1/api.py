"""Main API router for v1: includes all endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, users, games, admin

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["system"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(games.router, prefix="/users", tags=["sessions"])  # /users/{user_id}/sessions
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
