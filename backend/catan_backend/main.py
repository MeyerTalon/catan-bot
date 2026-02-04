from __future__ import annotations

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session

from . import models, schemas
from .db import Base, engine, db_session


def get_db() -> Session:
    with db_session() as session:
        yield session


def create_app() -> FastAPI:
    app = FastAPI(title="Catan Backend", version="0.1.0")

    # Ensure tables exist (for Supabase, you'd typically use migrations; this is a safety net)
    @app.on_event("startup")
    def _startup() -> None:  # type: ignore[override]
        Base.metadata.create_all(bind=engine)

    @app.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok"}

    # --- User endpoints (profiles linked to Supabase auth) -------------------

    @app.post("/users", response_model=schemas.UserRead, tags=["users"])
    def create_user(
        payload: schemas.UserCreate,
        db: Session = Depends(get_db),
    ) -> schemas.UserRead:
        existing = (
            db.query(models.User)
            .filter(models.User.id == payload.id)
            .or_(models.User.email == payload.email)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already exists.",
            )

        user = models.User(id=payload.id, email=payload.email)
        db.add(user)
        db.flush()
        return schemas.UserRead.model_validate(user)

    @app.get("/users/{user_id}", response_model=schemas.UserRead, tags=["users"])
    def get_user(user_id: str, db: Session = Depends(get_db)) -> schemas.UserRead:
        user = db.query(models.User).get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        return schemas.UserRead.model_validate(user)

    # --- Game session endpoints ----------------------------------------------

    @app.post(
        "/users/{user_id}/sessions",
        response_model=schemas.GameSessionRead,
        tags=["sessions"],
    )
    def create_session_for_user(
        user_id: str,
        payload: schemas.GameSessionCreate,
        db: Session = Depends(get_db),
    ) -> schemas.GameSessionRead:
        user = db.query(models.User).get(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        session = models.GameSession(user_id=user.id, state=payload.state)
        db.add(session)
        db.flush()
        return schemas.GameSessionRead.model_validate(session)

    @app.get(
        "/users/{user_id}/sessions",
        response_model=list[schemas.GameSessionRead],
        tags=["sessions"],
    )
    def list_sessions_for_user(
        user_id: str,
        db: Session = Depends(get_db),
    ) -> list[schemas.GameSessionRead]:
        sessions = (
            db.query(models.GameSession)
            .filter(models.GameSession.user_id == user_id)
            .order_by(models.GameSession.created_at.desc())
            .all()
        )
        return [schemas.GameSessionRead.model_validate(s) for s in sessions]

    return app


def run() -> None:
    uvicorn.run(
        "catan_backend.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


app = create_app()

