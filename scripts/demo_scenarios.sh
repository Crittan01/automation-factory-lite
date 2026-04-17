#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"

call_create() {
  local text="$1"
  curl -sS -X POST "${API_BASE}/api/requests" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"${text}\", \"requester\": \"demo.manager\"}" | jq .
}

echo "[1/3] Crear usuario en host1"
call_create "Crear usuario analista1 en ol9server1 sin sudo"

echo "[2/3] Instalar nginx en host2"
call_create "Instalar nginx en rocky9server1"

echo "[3/3] Instalar agente en ambos hosts (requiere aprobación)"
call_create "Instalar agente cockpit en ol9server1 y rocky9server1"

echo "Revisar pendientes en ${API_BASE}/api/approvals/pending"
