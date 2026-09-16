"""Health check endpoint."""

from fastapi import APIRouter

from app.schemas.response import HealthResponse

router = APIRouter()


@router.get('', response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check for the service.

    Returns:
        HealthResponse with status "ok".
    """
    return HealthResponse(status='ok')
