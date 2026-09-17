#!/usr/bin/env bash
# bootstrap a local vscode / cursor workspace: mise tools, uv + pnpm deps, env files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

log() {
  printf '==> %s\n' "$*"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

if [[ "$(id -u)" -eq 0 ]]; then
  die 'do not run setup.sh as root'
fi

if [[ "${1:-}" == '-h' || "${1:-}" == '--help' ]]; then
  cat <<'EOF'
usage: ./setup.sh

one-time local bootstrap for vscode / cursor:

  - install mise if missing, then the tools in mise.toml
  - sync the shared uv workspace env (.venv at the repo root: bot + backend)
  - install frontend pnpm dependencies from the lockfile
  - copy .env examples when local env files are absent
  - write workspace settings and recommend / install editor extensions

does not apply migrations, start servers, pull ollama models, or touch aws.
EOF
  exit 0
fi

copy_if_missing() {
  local src="$1"
  local dest="$2"
  if [[ -e "$dest" ]]; then
    log "keep existing ${dest#"$ROOT"/}"
    return
  fi
  cp "$src" "$dest"
  log "wrote ${dest#"$ROOT"/} (from $(basename "$src"); fill in secrets locally)"
}

ensure_mise_on_path() {
  local bindir="${HOME}/.local/bin"
  if [[ -d "$bindir" ]]; then
    case ":${PATH}:" in
      *":${bindir}:"*) ;;
      *) export PATH="${bindir}:${PATH}" ;;
    esac
  fi
}

install_mise() {
  if command -v mise >/dev/null 2>&1; then
    return
  fi
  if [[ -x "${HOME}/.local/bin/mise" ]]; then
    ensure_mise_on_path
    return
  fi
  if ! command -v curl >/dev/null 2>&1; then
    die 'curl is required to install mise (https://mise.jdx.dev/)'
  fi
  log 'installing mise'
  curl -fsSL https://mise.run | sh
  ensure_mise_on_path
  command -v mise >/dev/null 2>&1 || die 'mise installed but not on PATH; open a new terminal and re-run ./setup.sh'
}

write_vscode_workspace() {
  local dir="${ROOT}/.vscode"
  mkdir -p "$dir"

  if [[ ! -f "${dir}/extensions.json" ]]; then
    cat >"${dir}/extensions.json" <<'EOF'
{
  "recommendations": [
    "hverlin.mise-vscode",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "oxc.oxc-vscode",
    "bradlc.vscode-tailwindcss",
    "hashicorp.terraform"
  ]
}
EOF
    log 'wrote .vscode/extensions.json'
  else
    log 'keep existing .vscode/extensions.json'
  fi

  if [[ ! -f "${dir}/settings.json" ]]; then
    cat >"${dir}/settings.json" <<'EOF'
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.terminal.activateEnvironment": true,
  "ruff.nativeServer": "on",
  "ruff.configuration": "${workspaceFolder}/backend/pyproject.toml",
  "ruff.interpreter": ["${workspaceFolder}/.venv/bin/python"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "[typescript][typescriptreact][javascript][javascriptreact][json][jsonc][css]": {
    "editor.defaultFormatter": "oxc.oxc-vscode",
    "editor.formatOnSave": true
  },
  "oxc.fmt.configPath": "frontend/.oxfmtrc.json",
  "oxc.lint.configPath": "frontend/.oxlintrc.json",
  "js/ts.tsdk.path": "frontend/node_modules/typescript/lib",
  "terminal.integrated.env.osx": {
    "VIRTUAL_ENV": "${workspaceFolder}/.venv",
    "PATH": "${workspaceFolder}/.venv/bin:${env:HOME}/.local/share/mise/shims:${env:HOME}/.local/bin:${env:PATH}"
  },
  "terminal.integrated.env.linux": {
    "VIRTUAL_ENV": "${workspaceFolder}/.venv",
    "PATH": "${workspaceFolder}/.venv/bin:${env:HOME}/.local/share/mise/shims:${env:HOME}/.local/bin:${env:PATH}"
  },
  "mise.configureExtensionsAutomatically": true,
  "mise.configureExtensionsIncludeGlobalTools": false,
  "mise.configureExtensionsAutomaticallyIncludeList": [
    "charliermarsh.ruff"
  ]
}
EOF
    log 'wrote .vscode/settings.json'
  else
    log 'keep existing .vscode/settings.json'
  fi
}

install_editor_extensions() {
  local cli=""
  if command -v cursor >/dev/null 2>&1; then
    cli=cursor
  elif command -v code >/dev/null 2>&1; then
    cli=code
  else
    log 'no cursor/code CLI on PATH; install recommended extensions from the editor prompt'
    return
  fi

  log "installing editor extensions via ${cli}"
  local ext
  for ext in \
    hverlin.mise-vscode \
    ms-python.python \
    ms-python.vscode-pylance \
    charliermarsh.ruff \
    oxc.oxc-vscode \
    bradlc.vscode-tailwindcss \
    hashicorp.terraform
  do
    if "$cli" --install-extension "$ext" --force >/dev/null 2>&1; then
      log "installed ${ext}"
    else
      log "skip ${ext} (install from the editor if needed)"
    fi
  done
}

# --- run ---

log "workspace ${ROOT}"

install_mise
ensure_mise_on_path

export MISE_YES=1
log "mise $(mise --version | head -n1)"
mise trust "${ROOT}/mise.toml"
if [[ -f "${ROOT}/mise.lock" ]]; then
  log 'installing pinned tools from mise.lock'
  mise install --locked
else
  log 'installing tools from mise.toml'
  mise install
fi

eval "$(mise activate bash)"
export UV_PYTHON
UV_PYTHON="$(mise which python)"
log "uv will use ${UV_PYTHON}"

copy_if_missing "${ROOT}/backend/.env.example" "${ROOT}/backend/.env"
copy_if_missing "${ROOT}/frontend/.env.example" "${ROOT}/frontend/.env.local"

log 'syncing python and node dependencies'
mise run install

write_vscode_workspace
install_editor_extensions

log 'done'
cat <<EOF

next:
  1. edit backend/.env (DATABASE_URL, COGNITO_*)
  2. python interpreter: .venv/bin/python  (status bar, or "Python: Select Interpreter")
  3. mise run be:dev
  4. mise run fe:dev

reload the window if the new interpreter or extensions do not appear.
EOF
