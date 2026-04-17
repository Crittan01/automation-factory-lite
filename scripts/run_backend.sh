#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/load_env.sh"
load_env_file "${ROOT_DIR}/.env"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-18010}"

if ss -ltn | awk '{print $4}' | grep -Eq ":${BACKEND_PORT}$"; then
  echo "Error: port ${BACKEND_PORT} is already in use. Set BACKEND_PORT in .env."
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/apps/backend:${ROOT_DIR}"

cd "${ROOT_DIR}/apps/backend"
exec uvicorn app.main:app --reload --host "${BACKEND_HOST}" --port "${BACKEND_PORT}"
