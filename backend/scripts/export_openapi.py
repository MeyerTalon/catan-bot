"""Export the FastAPI OpenAPI schema for frontend type generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# importing the app builds the SQLAlchemy engine, which requires DATABASE_URL.
os.environ.setdefault(
    'DATABASE_URL', 'postgresql://export:export@localhost:5432/export'
)

from app.main import create_app


def _default_out() -> Path:
    """Return the default OpenAPI output path in the frontend package.

    Returns:
        Path to frontend/src/api/openapi.json.
    """
    return (
        Path(__file__).resolve().parents[2]
        / 'frontend'
        / 'src'
        / 'api'
        / 'openapi.json'
    )


def main(argv: list[str] | None = None) -> None:
    """Write the FastAPI OpenAPI schema as JSON.

    Args:
        argv: Optional CLI args. `--out PATH` (optional, default
            `frontend/src/api/openapi.json`) is the only flag.
    """
    parser = argparse.ArgumentParser(description='Export FastAPI OpenAPI schema.')
    parser.add_argument(
        '--out',
        type=Path,
        default=_default_out(),
        help='output JSON path (default: frontend/src/api/openapi.json)',
    )
    args = parser.parse_args(argv)

    app = create_app()
    spec = app.openapi()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
    print(f'wrote {args.out}')


if __name__ == '__main__':
    main(sys.argv[1:])
