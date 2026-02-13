"""User endpoints: create and get user profiles."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import user_service

router = APIRouter()


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Create a user profile (id and email). Fails if user already exists."""
    return user_service.create_user(db, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
) -> UserRead:
    """Get a user by UUID."""
    return user_service.get_user(db, user_id)
