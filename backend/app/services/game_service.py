"""Game session service: create and list sessions."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.game import game_crud
from app.crud.user import user_crud
from app.schemas.game import GameSessionCreate, GameSessionRead


def create_session(db: Session, user_id: str, payload: GameSessionCreate) -> GameSessionRead:
    """Create a game session for a user. Raises 404 if user not found."""
    user = user_crud.get(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    session = game_crud.create(db, user_id=user.id, state=payload.state)
    return GameSessionRead.model_validate(session)


def list_sessions(db: Session, user_id: str) -> list[GameSessionRead]:
    """List game sessions for a user, newest first."""
    sessions = game_crud.list_by_user_id(db, user_id)
    return [GameSessionRead.model_validate(s) for s in sessions]


class GameService:
    create_session = staticmethod(create_session)
    list_sessions = staticmethod(list_sessions)


game_service = GameService()
