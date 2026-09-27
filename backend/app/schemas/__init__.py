"""Pydantic schemas for API request/response validation."""

from app.schemas.auth import (
    AuthConfirmRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthMessageResponse,
    AuthRefreshRequest,
    AuthResendConfirmationRequest,
    AuthSessionResponse,
    AuthSignupRequest,
    AuthSignupResponse,
    AuthUser,
)
from app.schemas.game import (
    GameActionRequest,
    GameCreate,
    GameDetail,
    GameList,
    GameSeat,
    GameSummary,
)
from app.schemas.response import HealthResponse
from app.schemas.user import UserBase, UserRead

__all__ = [
    'AuthConfirmRequest',
    'AuthLoginRequest',
    'AuthLogoutRequest',
    'AuthMessageResponse',
    'AuthRefreshRequest',
    'AuthResendConfirmationRequest',
    'AuthSessionResponse',
    'AuthSignupRequest',
    'AuthSignupResponse',
    'AuthUser',
    'GameActionRequest',
    'GameCreate',
    'GameDetail',
    'GameList',
    'GameSeat',
    'GameSummary',
    'HealthResponse',
    'UserBase',
    'UserRead',
]
