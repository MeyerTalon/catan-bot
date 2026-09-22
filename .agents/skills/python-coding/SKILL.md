---
name: python-coding
description: >-
  Applies Python coding best practices when writing or editing Python.
  Trigger whenever the user asks to write, edit, refactor, or review
  Python code, invokes "/python-coding", or otherwise works in `.py`
  files in this repo. Use even when the request is implicit — if the task
  involves Python, apply it. Compose with other skills (e.g. concise) as needed.
---

# Python Coding

Write and edit Python that is clear, typed, documented, and consistent with this repo. Prefer existing patterns over inventing new ones.

## Rules

- **PEP 8 formatting via ruff.** Match PEP 8 (and existing repo style): naming, imports, spacing, line length. Format with `mise run be:format` (or `uv run ruff format` from `backend/`) and lint with `mise run be:lint` (config in `backend/pyproject.toml`). Prefer the project's established formatting over personal preference.
- **Single-quoted strings.** Use single quotes for string literals (`'foo'`), including f-strings. Prefer `'...'` over `"..."` unless the string contains a single quote (then use double quotes or escape). Docstrings stay triple-quoted per google-style convention.
- **Docstrings on functions.** Every function and method gets a docstring that states its purpose. Document Args/Returns/Raises when that information is not obvious from the signature and types. This repo uses Google-style docstrings (`Args:` / `Returns:` / `Raises:` sections) — match that unless the surrounding file differs.
- **Document CLI args in `main`.** In every runnable file (one with a `main` entry point behind `if __name__ == "__main__":`), the `main` docstring must document the command-line arguments it consumes — whether parsed from `sys.argv`, `argparse`, or Typer. List each argument with whether it is required/positional and its default, so the docstring alone tells the reader how to invoke the file.
- **Lowercase comments and docstrings.** Write all comment and docstring prose in lowercase — inline comments, module/file headers, and function/class docstrings alike (e.g. `# load configuration`, `"""selects the best available device."""`). Keep casing only where it is meaningful: identifiers and code references (`FastAPI`, `create_app`, `FileNotFoundError`), proper nouns and acronyms (Supabase, Postgres, JWT, CORS), code literals (`True`, `None`), and Google docstring section headers (`Args:` / `Returns:` / `Raises:`). Applies to code files only — `.py` and comments in configs — never to Markdown or other documentation files.
- **Type hints everywhere.** Annotate parameters, return types, and important locals/attributes. Prefer precise types over bare `Any` unless truly necessary. This repo uses `typing`-module generics (`Dict[str, Any]`, `Optional[str]`, `List[str]`) — match that rather than switching to lowercase built-in generics. Check backend types with `mise run be:typecheck` (or `uv run mypy` from `backend/`).
- **No redundant code.** Don't restate the obvious, keep dead code, wrap no-ops, or add comments that only repeat the code. Prefer the simplest correct form.
- **No unnecessary duplication.** Extract shared logic when the same behavior appears more than once (or clearly will). Don't abstract prematurely for a one-off.
- **Manage dependencies with uv, in one workspace.** The repo-root `pyproject.toml` is a virtual uv workspace root with `backend/` and `engine/` as members: one `uv.lock` and one `.venv`, both at the root. Deps go in the member's `pyproject.toml` (`uv add <package>` / `uv add --dev <package>` / `uv remove` from `backend/` or `engine/`). Sync with `mise run sync` (`uv sync --frozen --all-packages --all-groups`), run Python through `mise run be:*` / `mise run ge:*` or `uv run` from the member's directory, and commit the root `uv.lock`. Never create a second venv or lockfile under a member; do not use pip, conda, or poetry unless asked.
- **Unit tests for critical functions.** When writing or changing a function whose failure would break API, auth, persistence, or game-rule behavior, add a lightweight unit test that confirms its core behavior. Tests must run in seconds: tiny inputs, no network, no real database. Use `mise run be:test` (or `uv run pytest` from `backend/`; plain test functions with asserts — no test classes unless grouping helps). Put backend tests in `backend/tests/test_<module>.py` and engine tests in `engine/tests/test_<module>.py` (`mise run ge:test`). Skip tests for trivial glue or one-off scripts.
- **Follow existing patterns.** Mirror nearby modules for FastAPI routers, SQLAlchemy models, Pydantic schemas, CRUD, services, and `engine` models/actions before introducing a new approach.

## Anti-goals

Don't skip types or docstrings to save time, don't copy-paste with slight variations, and don't "improve" working code into a different style than the surrounding package. Clean ≠ novel. Don't write heavy tests — anything that hits the network, a real database, or takes more than a few seconds defeats the purpose.
