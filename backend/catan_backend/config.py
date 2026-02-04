from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, AnyUrl


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    database_url: AnyUrl
    supabase_project_url: Optional[AnyUrl] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """
    Load settings from environment.

    Expected environment variables:
      - DATABASE_URL: Postgres connection string (Supabase).
      - SUPABASE_URL: Supabase project URL (optional, mainly for frontend).
      - SUPABASE_ANON_KEY: Supabase anon key (optional, mainly for frontend).
      - SUPABASE_SERVICE_ROLE_KEY: Service role key (optional, backend-only).
      - ENVIRONMENT: "development" | "production"
    """

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable must be set.")

    return Settings(
        database_url=database_url,
        supabase_project_url=os.environ.get("SUPABASE_URL"),
        supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY"),
        supabase_service_role_key=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        environment=os.environ.get("ENVIRONMENT", "development"),
    )

