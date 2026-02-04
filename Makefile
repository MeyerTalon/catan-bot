.PHONY: help supabase-start supabase-stop db-reset-local db-push-local db-push-remote

help:
	@echo "Supabase / DB helpers:"
	@echo "  make supabase-start   # start local Supabase stack (Docker)"
	@echo "  make supabase-stop    # stop local Supabase stack"
	@echo "  make db-reset-local   # reset local DB using migrations"
	@echo "  make db-push-local    # apply migrations to local DB"
	@echo "  make db-push-remote   # apply migrations to remote DB via SUPABASE_DB_URL"

supabase-start:
	supabase start

supabase-stop:
	supabase stop

db-reset-local:
	supabase db reset

db-push-local:
	supabase db push

db-push-remote:
	@if [ -z "$$SUPABASE_DB_URL" ]; then echo "SUPABASE_DB_URL is not set"; exit 1; fi
	supabase db push --db-url "$$SUPABASE_DB_URL"

