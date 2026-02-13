"""Game session CRUD operations."""

from __future__ import annotations

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.models.game import GameSession


def create(db: Session, *, user_id: uuid.UUID, state: dict) -> GameSession:
    """Create a game session. Caller must commit or use within db_session."""
    session = GameSession(user_id=user_id, state=state)
    db.add(session)
    db.flush()
    return session


def list_by_user_id(db: Session, user_id: uuid.UUID | str) -> List[GameSession]:
    """List game sessions for a user, newest first."""
    q = db.query(GameSession).filter(GameSession.user_id == user_id)
    return q.order_by(GameSession.created_at.desc()).all()


class GameCRUD:
    create = staticmethod(create)
    list_by_user_id = staticmethod(list_by_user_id)


game_crud = GameCRUD()
