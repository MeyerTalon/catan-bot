"""Game session endpoints: create and list sessions for a user."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.game import GameSessionCreate, GameSessionRead
from app.services.game_service import game_service

router = APIRouter()


@router.post("/{user_id}/sessions", response_model=GameSessionRead)
def create_session_for_user(
    user_id: str,
    payload: GameSessionCreate,
    db: Session = Depends(get_db),
) -> GameSessionRead:
    """Create a game session for a user."""
    return game_service.create_session(db, user_id, payload)


@router.get("/{user_id}/sessions", response_model=list[GameSessionRead])
def list_sessions_for_user(
    user_id: str,
    db: Session = Depends(get_db),
) -> list[GameSessionRead]:
    """List game sessions for a user, newest first."""
    return game_service.list_sessions(db, user_id)
