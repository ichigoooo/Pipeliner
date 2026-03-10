#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_HOST="127.0.0.1"
API_PORT="8000"
WEB_PORT="3000"

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$env_file"
    set +a
  fi
}

require_cmd() {
  local cmd_name="$1"
  if ! command -v "$cmd_name" >/dev/null 2>&1; then
    echo "missing required command: $cmd_name" >&2
    exit 1
  fi
}

list_port_pids() {
  local port="$1"
  lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true
}

process_command() {
  local pid="$1"
  ps -p "$pid" -o command= 2>/dev/null || true
}

process_ppid() {
  local pid="$1"
  ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true
}

is_managed_pid() {
  local pid="$1"
  local command
  local parent_pid
  local parent_command
  command="$(process_command "$pid")"

  [[ -n "$command" ]] || return 1

  case "$command" in
    *"uvicorn pipeliner.app:create_app"*|*"next dev --hostname 0.0.0.0 --port $WEB_PORT"*|*"next-server"*)
      [[ "$command" == *"$ROOT_DIR"* ]] || [[ "$command" == *"next-server"* ]] || return 1
      return 0
      ;;
  esac

  parent_pid="$(process_ppid "$pid")"
  [[ -n "$parent_pid" ]] || return 1

  parent_command="$(process_command "$parent_pid")"
  [[ -n "$parent_command" ]] || return 1

  case "$parent_command" in
    *"$ROOT_DIR"*uvicorn\ pipeliner.app:create_app*|*"$ROOT_DIR"*next\ dev\ --hostname\ 0.0.0.0\ --port\ "$WEB_PORT"*)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_port_available() {
  local port="$1"
  local service_name="$2"
  local pids
  pids="$(list_port_pids "$port")"

  [[ -n "$pids" ]] || return 0

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    if ! is_managed_pid "$pid"; then
      echo "port $port is already in use by a non-Pipeliner process: $(process_command "$pid")" >&2
      echo "please stop that process or change the port in .env before retrying" >&2
      exit 1
    fi
  done <<< "$pids"

  echo "stopping existing $service_name process on port $port"
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    kill "$pid" >/dev/null 2>&1 || true
  done <<< "$pids"

  for _ in {1..20}; do
    if [[ -z "$(list_port_pids "$port")" ]]; then
      return 0
    fi
    sleep 0.2
  done

  echo "failed to free port $port for $service_name" >&2
  exit 1
}

cleanup() {
  if [[ -n "${API_PID:-}" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${WEB_PID:-}" ]]; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

cd "$ROOT_DIR"

load_env_file "$ROOT_DIR/.env"
load_env_file "$ROOT_DIR/web/.env.local"

API_HOST="${PIPELINER_API_HOST:-$API_HOST}"
API_PORT="${PIPELINER_API_PORT:-$API_PORT}"
WEB_PORT="${PIPELINER_WEB_PORT:-$WEB_PORT}"

export PIPELINER_API_BASE_URL="${PIPELINER_API_BASE_URL:-http://$API_HOST:$API_PORT}"
export NEXT_PUBLIC_PIPELINER_API_BASE_URL="${NEXT_PUBLIC_PIPELINER_API_BASE_URL:-$PIPELINER_API_BASE_URL}"

require_cmd uv
require_cmd npm
require_cmd lsof
require_cmd ps

ensure_port_available "$API_PORT" "backend"
ensure_port_available "$WEB_PORT" "frontend"

uv sync
uv run alembic upgrade head
uv run pipeliner db-init

uv run uvicorn pipeliner.app:create_app \
  --factory \
  --reload \
  --host "$API_HOST" \
  --port "$API_PORT" &
API_PID="$!"

cd "$ROOT_DIR/web"
npm install
npm run dev -- --hostname 0.0.0.0 --port "$WEB_PORT" &
WEB_PID="$!"

echo "backend: http://$API_HOST:$API_PORT"
echo "frontend: http://127.0.0.1:$WEB_PORT"

wait "$WEB_PID"
