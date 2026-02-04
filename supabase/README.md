# Supabase workflow

This project uses Supabase Postgres for persistence. The SQL migrations in
`supabase/migrations` are the **source of truth** for the database schema.

## Prerequisites

- Supabase CLI installed (`npm install -g supabase` or see official docs)
- Docker (for running Supabase locally)

## Local development

From the repo root you can use the `Makefile` helpers:

```bash
make supabase-start    # start local Supabase stack
make db-reset-local    # recreate local DB from migrations
```

Once running, point your backend `DATABASE_URL` at the local database (see
Supabase CLI output for connection details).

## Making schema changes

1. Start local Supabase if it is not already running:

   ```bash
   make supabase-start
   ```

2. Apply your schema changes to the local database (via SQL or Supabase UI).

3. Generate a migration file capturing the diff:

   ```bash
   # replace NAME with a short description
   supabase db diff --file supabase/migrations/$(date +%Y%m%dT%H%M%S)_NAME.sql
   ```

4. Reset local DB to ensure the migration sequence is valid:

   ```bash
   make db-reset-local
   ```

5. Run backend tests and the app against this schema.

6. Commit the new migration file together with the corresponding code changes.

## Applying migrations to remote environments

CI is configured to run:

```bash
supabase db push --db-url "$SUPABASE_DB_URL"
```

on pushes to `main`. You can also run this manually from your machine:

```bash
export SUPABASE_DB_URL="postgresql://user:password@host:5432/dbname"
make db-push-remote
```

Only run this against non-production or production databases that are backed up
and managed through your normal release process.

