"""User endpoints: create and get user profiles."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserRead
from app.services.user_service import user_service

router = APIRouter()


@router.post("", response_model=UserRead)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> UserRead:
    """Create a user profile (id and email).

    Args:
        payload: User creation data containing id (UUID) and email.
        db: Database session (injected dependency).

    Returns:
        Created user profile as UserRead schema.

    Raises:
        HTTPException: 400 if user already exists.

    Note:
        This endpoint is public - users create their profile after Supabase signup.
    """
    return user_service.create_user(db, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Get a user by UUID.

    Args:
        user_id: User UUID as string (from path parameter).
        current_user: Authenticated user (injected dependency).
        db: Database session (injected dependency).

    Returns:
        User profile as UserRead schema.

    Raises:
        HTTPException: 403 if trying to access another user's profile.
        HTTPException: 404 if user not found.

    Note:
        Requires Authorization header with valid Supabase JWT token.
        Users can only access their own profile.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' profiles.",
        )
    return user_service.get_user(db, user_id)
