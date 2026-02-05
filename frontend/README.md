# Frontend (React + Vite + Supabase)

React frontend for the Catan app. Built with Vite and TypeScript; designed to use Supabase for auth and (optionally) the backend API for users and game sessions. Deployed to Vercel.

## Tech stack

- **React** 18
- **TypeScript**
- **Vite** 5 – dev server and production build
- **@supabase/supabase-js** – Supabase client (auth, optional realtime/storage)
- **ESLint** – linting (React hooks, React refresh)

No UI framework is installed by default; the app uses custom CSS (e.g. `styles.css`). You can add Tailwind or another CSS approach later.

## Structure

```
frontend/
├── index.html           # Single-page app shell; mounts #root and loads src/main.tsx
├── package.json         # Scripts and dependencies
├── package-lock.json
├── tsconfig.json        # TypeScript config
├── vite.config.ts       # Vite config (React plugin, dev server port 5173)
├── src/
│   ├── main.tsx         # Entry: React root, renders <AuthScreen />
│   ├── styles.css       # Global styles
│   └── screens/
│       └── AuthScreen.tsx   # Landing / auth UI (e.g. “Play Catan”)
├── public/              # Static assets (if added)
└── README.md            # This file
```

### Key files

| File | Role |
|------|------|
| **index.html** | HTML shell; `<div id="root">` and `<script type="module" src="/src/main.tsx">`. Vite serves this and injects the bundled app. |
| **vite.config.ts** | Uses `@vitejs/plugin-react-swc`; dev server runs on port **5173**. |
| **src/main.tsx** | Creates React root, renders `<AuthScreen />` inside `StrictMode`, and imports `styles.css`. |
| **src/screens/AuthScreen.tsx** | Landing screen: title, subtitle, “Play Catan” button (placeholder handler), and hint text. Intended to be extended with Supabase sign-in/sign-up and navigation to game or lobby. |
| **src/styles.css** | Global styles (e.g. layout, landing card, buttons). Referenced from `main.tsx`. |

The root README mentions `src/lib/supabaseClient.ts` for the Supabase JS client; that file may be added when you wire up auth. Until then, the app runs without it.

## Scripts

From the `frontend/` directory:

| Command | Description |
|---------|-------------|
| `npm install` | Install dependencies. |
| `npm run dev` | Start Vite dev server (default: http://localhost:5173). Uses `BROWSER="Google Chrome"` if set. |
| `npm run build` | Production build; output in `dist/`. |
| `npm run preview` | Serve the `dist/` build locally to test production. |
| `npm run lint` | Run ESLint on `src` (`.ts`, `.tsx`), max warnings 0. |

## Environment variables

For Supabase (auth, etc.) you’ll use env vars prefixed with `VITE_` so Vite exposes them to the client.

Configure in Vercel (and in `.env.local` for local dev):

| Variable | Description |
|----------|-------------|
| `VITE_SUPABASE_URL` | Supabase project URL (e.g. `https://<project-ref>.supabase.co`). |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon (public) key. |

Create `frontend/.env.local` for local development (do not commit secrets). Example:

```bash
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
```

Restart the dev server after changing `.env.local`.

## How to use

### 1. Install dependencies

```bash
cd frontend
npm install
```

### 2. (Optional) Configure Supabase for local dev

Create `frontend/.env.local` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` if you’re using Supabase auth or API.

### 3. Run the dev server

```bash
npm run dev
```

Open http://localhost:5173. You should see the landing screen and “Play Catan”; the button handler is a placeholder (e.g. `console.log`).

### 4. Build for production

```bash
npm run build
```

Artifacts go to `dist/`. Test with:

```bash
npm run preview
```

### 5. Deploy

The repo’s CI/CD deploys the **frontend** to Vercel on pushes to `main`. Configure the Vercel project to use the `frontend/` directory as the root and set `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` (and any other env) in the Vercel dashboard.

## Backend integration

The backend runs separately (see `backend/README.md`) and exposes a REST API (e.g. `/users`, `/users/{id}/sessions`). To call it from the frontend:

- In development, backend is often at `http://localhost:8000`. Use `fetch` or a client (e.g. axios) and optionally a `VITE_API_URL` env var.
- Ensure CORS is allowed on the backend for the frontend origin (e.g. `http://localhost:5173` and your Vercel domain). FastAPI can use `CORSMiddleware` in `app/main.py` if not already configured.

## Linting

ESLint runs over `src` with React hooks and React refresh plugins. Fix issues before committing:

```bash
npm run lint
```
