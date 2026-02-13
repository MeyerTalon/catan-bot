"""Game session endpoints: create and list sessions for a user."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.game import GameSessionCreate, GameSessionRead
from app.services.game_service import game_service

router = APIRouter()


@router.post("/{user_id}/sessions", response_model=GameSessionRead)
def create_session_for_user(
    user_id: str,
    payload: GameSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameSessionRead:
    """Create a game session for a user.

    Args:
        user_id: User UUID as string (from path parameter).
        payload: Game session creation data containing optional initial state.
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        Created game session as GameSessionRead schema.

    Raises:
        HTTPException: 403 if trying to create session for another user.
        HTTPException: 404 if user not found.

    Note:
        Requires Authorization header with valid Supabase JWT token.
        Users can only create their own sessions.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create sessions for other users.",
        )
    return game_service.create_session(db, user_id, payload)


@router.get("/{user_id}/sessions", response_model=list[GameSessionRead])
def list_sessions_for_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GameSessionRead]:
    """List game sessions for a user, newest first.

    Args:
        user_id: User UUID as string (from path parameter).
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        List of game sessions as GameSessionRead schemas, ordered by created_at descending.

    Raises:
        HTTPException: 403 if trying to access another user's sessions.

    Note:
        Requires Authorization header with valid Supabase JWT token.
        Users can only list their own sessions.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' sessions.",
        )
    return game_service.list_sessions(db, user_id)
