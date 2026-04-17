#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/load_env.sh"
load_env_file "${ROOT_DIR}/.env"

FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-13000}"
BACKEND_PORT="${BACKEND_PORT:-18010}"
NEXT_PUBLIC_API_BASE_URL="${NEXT_PUBLIC_API_BASE_URL:-http://127.0.0.1:${BACKEND_PORT}}"

if ss -ltn | awk '{print $4}' | grep -Eq ":${FRONTEND_PORT}$"; then
  echo "Error: port ${FRONTEND_PORT} is already in use. Set FRONTEND_PORT in .env."
  exit 1
fi

export NEXT_PUBLIC_API_BASE_URL

cd "${ROOT_DIR}/apps/frontend"
exec npm run dev -- --hostname "${FRONTEND_HOST}" --port "${FRONTEND_PORT}"
