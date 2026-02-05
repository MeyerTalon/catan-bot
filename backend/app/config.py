from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv

# Load backend/.env so env vars are available without exporting manually.
_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir / ".env")


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    database_url: str
    supabase_project_url: Optional[str] = None
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
    
    database_url = os.environ.get("SUPABASE_DATABASE_URL")
    if not database_url:
        raise RuntimeError("SUPABASE_DATABASE_URL environment variable must be set.")
    if database_url.strip().lower().startswith("https://"):
        raise RuntimeError(
            "SUPABASE_DATABASE_URL must be a Postgres connection string (e.g. postgresql://... or postgresql+psycopg2://...), "
            "not the Supabase project URL (https://...). Get the DB URL from Supabase: Project Settings → Database → Connection string."
        )

    return Settings(
        database_url=database_url,
        supabase_anon_key=os.environ.get("SUPABASE_ANON_KEY"),
        environment=os.environ.get("ENVIRONMENT", "development"),
    )

