#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/.run-logs"
mkdir -p "${LOG_DIR}"

# shellcheck disable=SC1091
source "${ROOT_DIR}/scripts/lib/load_env.sh"
load_env_file "${ROOT_DIR}/.env"

BACKEND_PORT="${BACKEND_PORT:-18010}"
FRONTEND_PORT="${FRONTEND_PORT:-13000}"
SERVICENOW_SIM_PORT="${SERVICENOW_SIM_PORT:-18095}"

cleanup() {
  jobs -p | xargs -r kill 2>/dev/null || true
}

trap cleanup EXIT INT TERM

"${ROOT_DIR}/scripts/run_servicenow_sim.sh" >"${LOG_DIR}/servicenow-sim.log" 2>&1 &
"${ROOT_DIR}/scripts/run_backend.sh" >"${LOG_DIR}/backend.log" 2>&1 &
"${ROOT_DIR}/scripts/run_frontend.sh" >"${LOG_DIR}/frontend.log" 2>&1 &

sleep 2

echo "Automation Factory Lite UI: http://127.0.0.1:${FRONTEND_PORT}/"
echo "AFL API docs: http://127.0.0.1:${BACKEND_PORT}/docs"
echo "ServiceNow SIM health: http://127.0.0.1:${SERVICENOW_SIM_PORT}/health"
echo "Logs: ${LOG_DIR}"

wait -n
