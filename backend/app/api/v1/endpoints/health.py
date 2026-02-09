"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def health() -> dict:
    """Liveness check for the service.

    Returns:
        dict: {"status": "ok"}.
    """
    return {"status": "ok"}
