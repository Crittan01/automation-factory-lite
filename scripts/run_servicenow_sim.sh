#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/load_env.sh"
load_env_file "${ROOT_DIR}/.env"

SERVICENOW_SIM_HOST="${SERVICENOW_SIM_HOST:-0.0.0.0}"
SERVICENOW_SIM_PORT="${SERVICENOW_SIM_PORT:-18095}"

if ss -ltn | awk '{print $4}' | grep -Eq ":${SERVICENOW_SIM_PORT}$"; then
  echo "Error: port ${SERVICENOW_SIM_PORT} is already in use. Set SERVICENOW_SIM_PORT in .env."
  exit 1
fi

export PYTHONPATH="${ROOT_DIR}/apps/backend:${ROOT_DIR}"

cd "${ROOT_DIR}"
exec uvicorn services.servicenow_sim.api:app --host "${SERVICENOW_SIM_HOST}" --port "${SERVICENOW_SIM_PORT}" --reload
