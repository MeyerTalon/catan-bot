"""Application configuration loaded from environment variables.

Loads backend/.env automatically. Use get_settings() for a cached Settings instance.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# load backend/.env so env vars are available without exporting manually.
_backend_dir = Path(__file__).resolve().parent.parent.parent
load_dotenv(_backend_dir / '.env')


class Settings(BaseModel):
    """Application settings loaded from environment variables.

    Attributes:
        database_url: Postgres connection string (RDS). Required.
        cognito_region: AWS region for the Cognito user pool.
        cognito_user_pool_id: Cognito user pool id. Required for auth.
        cognito_client_id: Cognito app client id. Required for auth.
        cognito_client_secret: Cognito app client secret. Optional (public clients omit it).
        cognito_endpoint_url: override for the Cognito API endpoint. Only for a local
            emulator; None uses the real AWS endpoint.
        cognito_jwks_url: override for the JWKS url used to verify tokens. Only for a
            local emulator; None derives it from the issuer.
        environment: "development" or "production". Defaults to "development".
    """

    database_url: str
    cognito_region: str = 'us-west-2'
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None
    cognito_client_secret: str | None = None
    cognito_endpoint_url: str | None = None
    cognito_jwks_url: str | None = None
    environment: str = 'development'

    @property
    def is_production(self) -> bool:
        """Whether the current environment is production.

        Returns:
            True if environment is "production" (case-insensitive), else False.
        """
        return self.environment.lower() == 'production'

    @property
    def cognito_configured(self) -> bool:
        """Whether Cognito auth settings are present.

        Returns:
            True if user pool id and client id are both set.
        """
        return bool(self.cognito_user_pool_id and self.cognito_client_id)

    @property
    def cognito_issuer(self) -> str:
        """JWT issuer for the configured Cognito user pool.

        Returns:
            Cognito IdP issuer URL.

        Raises:
            RuntimeError: If the user pool id is missing.
        """
        if not self.cognito_user_pool_id:
            raise RuntimeError('COGNITO_USER_POOL_ID is not set.')
        return (
            f'https://cognito-idp.{self.cognito_region}.amazonaws.com/'
            f'{self.cognito_user_pool_id}'
        )

    @property
    def jwks_url(self) -> str:
        """JWKS url for verifying tokens from the configured user pool.

        Returns:
            COGNITO_JWKS_URL when set (local emulator), else the issuer's well-known url.

        Raises:
            RuntimeError: If no override is set and the user pool id is missing.
        """
        return self.cognito_jwks_url or f'{self.cognito_issuer}/.well-known/jwks.json'


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment.

    Loads from os.environ and backend/.env. Requires DATABASE_URL to be set and
    to be a Postgres connection string.

    Returns:
        Cached Settings instance with database_url, Cognito settings, and environment.

    Raises:
        RuntimeError: If DATABASE_URL is missing or starts with https://.
    """
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError('DATABASE_URL environment variable must be set.')
    if database_url.strip().lower().startswith('https://'):
        raise RuntimeError(
            'DATABASE_URL must be a Postgres connection string '
            '(e.g. postgresql://... or postgresql+psycopg2://...).'
        )

    return Settings(
        database_url=database_url,
        cognito_region=os.environ.get('COGNITO_REGION', 'us-west-2'),
        cognito_user_pool_id=os.environ.get('COGNITO_USER_POOL_ID'),
        cognito_client_id=os.environ.get('COGNITO_CLIENT_ID'),
        cognito_client_secret=os.environ.get('COGNITO_CLIENT_SECRET'),
        cognito_endpoint_url=os.environ.get('COGNITO_ENDPOINT_URL'),
        cognito_jwks_url=os.environ.get('COGNITO_JWKS_URL'),
        environment=os.environ.get('ENVIRONMENT', 'development'),
    )
