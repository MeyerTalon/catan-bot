# Frontend (React + Vite)

React frontend for the Catan app. Built with Vite and TypeScript. Auth goes through the FastAPI backend (Amazon Cognito). Production static files are served from S3 + CloudFront.

Wire types are generated from the backend OpenAPI schema. Do not hand-edit `src/api/schema.d.ts` or `src/api/openapi.json`.

## Tech stack

- **React** 18
- **TypeScript**
- **Vite** 5
- **pnpm** – package manager (`pnpm-lock.yaml`)
- **Tailwind CSS** 4 (`@tailwindcss/vite`) + **shadcn/ui** (`radix-nova` preset, Lucide icons) – styling; see [Styling](#styling)
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
│   ├── components/
│   │   ├── ui/              # shadcn/ui components (CLI-generated; re-add, don't hand-edit)
│   │   └── *.tsx            # App-specific shared components (auth shell, hex mark)
│   ├── lib/
│   │   ├── session.ts       # Local session storage for Cognito tokens
│   │   └── utils.ts         # shadcn `cn()` helper
│   ├── screens/             # Auth + game UI
│   ├── index.css            # Tailwind entry + theme tokens (the only stylesheet)
│   ├── App.tsx
│   └── main.tsx
├── components.json          # shadcn/ui config (aliases, preset, css path)
├── Dockerfile               # local stack: pnpm build → nginx (stands in for S3 + CloudFront)
├── nginx.conf               # static files, /api/* → backend with the prefix stripped, SPA fallback
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

## Styling

One theme, dark only ("Harbor": blue-grey ground, wheat-gold accent). Every colour, radius, and font is a CSS variable in `src/index.css` (`:root` block); components reference only the shadcn token names (`bg-background`, `text-muted-foreground`, `bg-primary`, …), so a theme change is a one-block edit. `<html class="dark">` in `index.html` turns on the components' `dark:` variants. Fonts are self-hosted via `@fontsource-variable/*` (Instrument Sans for text, Bricolage Grotesque for headings via `font-heading`).

Import project modules through the `@/` alias (`@/components/ui/button`, `@/lib/session`); it is configured in `tsconfig.json` and `vite.config.ts`.

Add shadcn components with the CLI from `frontend/` (they land in `src/components/ui/` and are exempt from the `react/only-export-components` lint rule):

```bash
pnpm dlx shadcn@latest add dialog
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
./scripts/setup.sh  # from the repo root, once
mise run fe:dev
```
