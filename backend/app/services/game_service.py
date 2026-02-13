"""Game session service: create and list sessions."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.game import game_crud
from app.crud.user import user_crud
from app.schemas.game import GameSessionCreate, GameSessionRead


def create_session(db: Session, user_id: str, payload: GameSessionCreate) -> GameSessionRead:
    """Create a game session for a user.

    Args:
        db: Database session.
        user_id: User UUID as string.
        payload: Game session creation data containing optional initial state.

    Returns:
        Created game session as GameSessionRead schema.

    Raises:
        HTTPException: 404 if user not found.
    """
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session = game_crud.create(db, user_id=user.id, state=payload.state)
    return GameSessionRead.model_validate(session)


def list_sessions(db: Session, user_id: str) -> list[GameSessionRead]:
    """List game sessions for a user, newest first.

    Args:
        db: Database session.
        user_id: User UUID as string.

    Returns:
        List of game sessions as GameSessionRead schemas, ordered by created_at descending.
    """
    sessions = game_crud.list_by_user_id(db, user_id)
    return [GameSessionRead.model_validate(s) for s in sessions]


class GameService:
    """Game session service for creating and managing Catan game sessions.

    Provides business logic for game session operations tied to user profiles.
    """

    create_session = staticmethod(create_session)
    list_sessions = staticmethod(list_sessions)


game_service = GameService()
