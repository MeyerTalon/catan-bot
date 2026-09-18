"""User endpoints: get the authenticated user's profile."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.user import UserRead
from app.services.user_service import user_service

router = APIRouter()


@router.get('/{user_id}', response_model=UserRead)
def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    """Get a user by UUID.

    profiles are created by signup and login; there is no public create route.

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
        Requires Authorization header with a valid Cognito access token.
        Users can only access their own profile.
    """
    if str(current_user.id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other users' profiles.",
        )
    return user_service.get_user(db, user_id)
