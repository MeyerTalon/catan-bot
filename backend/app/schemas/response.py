"""Standard API response wrappers."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Liveness payload for GET /health.

    Attributes:
        status: Service status string.
    """

    status: str
