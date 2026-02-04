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

