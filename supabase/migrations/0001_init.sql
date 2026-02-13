-- Initial Supabase schema for Catan app
-- This file is a placeholder; adjust to match your Supabase setup.

create table if not exists public.users (
  id uuid primary key,
  email text not null unique,
  created_at timestamptz default now()
);

create table if not exists public.game_sessions (
  id serial primary key,
  user_id uuid not null references public.users (id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists game_sessions_user_id_idx on public.game_sessions (user_id);

-- Enable Row Level Security (RLS) on all tables
alter table public.users enable row level security;
alter table public.game_sessions enable row level security;

-- Users: allow access only to the row matching the authenticated user (id = auth.uid())
create policy "Users: select own row"
  on public.users for select
  using (auth.uid() = id);

create policy "Users: insert own row"
  on public.users for insert
  with check (auth.uid() = id);

create policy "Users: update own row"
  on public.users for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- Game sessions: allow access only to rows owned by the authenticated user (user_id = auth.uid())
create policy "Game sessions: select own"
  on public.game_sessions for select
  using (auth.uid() = user_id);

create policy "Game sessions: insert own"
  on public.game_sessions for insert
  with check (auth.uid() = user_id);

create policy "Game sessions: update own"
  on public.game_sessions for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "Game sessions: delete own"
  on public.game_sessions for delete
  using (auth.uid() = user_id);
