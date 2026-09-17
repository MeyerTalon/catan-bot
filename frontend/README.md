# Frontend (React + Vite)

React frontend for the Catan app. Built with Vite and TypeScript. Auth goes through the FastAPI backend (Amazon Cognito). Production static files are served from S3 + CloudFront.

Wire types are generated from the backend OpenAPI schema. Do not hand-edit `src/api/schema.d.ts` or `src/api/openapi.json`.

## Tech stack

- **React** 18
- **TypeScript**
- **Vite** 5
- **pnpm** – package manager (`pnpm-lock.yaml`)
- **openapi-fetch** + **openapi-typescript** – typed client from FastAPI `/openapi.json`
- **oxlint** + **oxfmt** – linting and formatting (`.oxlintrc.json`, `.oxfmtrc.json`; 80 cols, prettier-compatible style)

## Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── openapi.json     # Exported from FastAPI (committed)
│   │   ├── schema.d.ts      # Generated TS types (committed)
│   │   └── client.ts        # openapi-fetch client
│   ├── lib/session.ts       # Local session storage for Cognito tokens
│   ├── screens/             # Auth + game UI
│   ├── App.tsx
│   └── main.tsx
└── README.md
```

## Scripts

Prefer `mise run fe:*` from the repo root. Direct pnpm equivalents from `frontend/`:

| Command | Description |
|---------|-------------|
| `mise run fe:install` / `pnpm install` | Install dependencies. |
| `mise run fe:dev` / `pnpm run dev` | Vite dev server (http://localhost:5173). |
| `mise run fe:build` / `pnpm run build` | Production build → `dist/`. |
| `mise run fe:preview` / `pnpm run preview` | Serve `dist/` locally. |
| `mise run fe:lint` / `pnpm run lint` | oxlint on `src`; warnings fail (`pnpm run lint:fix` autofixes). |
| `mise run fe:format` / `pnpm run format` | oxfmt in place (`fe:format-check` / `format:check` to verify). |
| `mise run fe:typecheck` / `pnpm run typecheck` | `tsc --noEmit`. |
| `mise run fe:check` | format-check + lint + typecheck (what CI runs). |
| `mise run api` / `pnpm run generate:api` | Export OpenAPI (backend) and regenerate `src/api/schema.d.ts`. |

After backend schema changes:

```bash
mise run api
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `VITE_BACKEND_URL` | Backend origin (default in code: `http://localhost:8000`). |

Create `frontend/.env.local` for local development:

```bash
VITE_BACKEND_URL=http://localhost:8000
```

Production builds in CI use the `VITE_BACKEND_URL` GitHub secret (ALB URL).

## Running

```bash
./setup.sh          # from the repo root, once
mise run fe:dev
```
