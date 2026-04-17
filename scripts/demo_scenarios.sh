#!/usr/bin/env bash
set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-18010}"
API_BASE="${API_BASE:-http://localhost:${BACKEND_PORT}}"

call_create() {
  local text="$1"
  local ticket="$2"
  curl -sS -X POST "${API_BASE}/api/requests" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"${text}\", \"requester\": \"demo.manager\", \"ticket_id\": \"${ticket}\"}" | jq .
}

echo "[1/6] Crear usuario en host1"
call_create "Crear usuario analista1 en ol9server1 sin sudo" "AFL-DEMO-001"

echo "[2/6] Instalar nginx en host2"
call_create "Instalar nginx en rocky9server1" "AFL-DEMO-002"

echo "[3/6] Instalar agente en ambos hosts (requiere aprobación)"
call_create "Instalar agente cockpit en ol9server1 y rocky9server1" "AFL-DEMO-003"

echo "[4/6] Crear carpeta segura"
call_create "Crear carpeta /opt/automation_factory_lite/jobs/demo en rocky9server1" "AFL-DEMO-004"

echo "[5/6] Diagnostico uptime"
call_create "Obtener uptime en ol9server1" "AFL-DEMO-005"

echo "[6/6] ServiceNow sim: seed + agent run"
curl -sS -X POST "${API_BASE}/api/servicenow/cases/seed" | jq '.[]? | {number, state, short_description}'
curl -sS -X POST "${API_BASE}/api/servicenow/agent/run?limit=15" | jq .

echo "Revisar pendientes en ${API_BASE}/api/approvals/pending"
