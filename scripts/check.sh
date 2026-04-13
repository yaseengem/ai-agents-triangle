#!/usr/bin/env bash
# check.sh — Report the status of all Neural services (processes + ports)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$REPO_ROOT/scripts/pids"

# ── Load port config from .env ────────────────────────────────────────────────
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -o allexport
  source "$REPO_ROOT/.env"
  set +o allexport
fi

CLAIMS_API_PORT="${CLAIMS_API_PORT:-8001}"
UNDERWRITING_API_PORT="${UNDERWRITING_API_PORT:-8002}"
LOAN_API_PORT="${LOAN_API_PORT:-8003}"
FRONTEND_PORT=5173

# ── Colours ───────────────────────────────────────────────────────────────────
GRN='\033[0;32m'
RED='\033[0;31m'
YLW='\033[1;33m'
CYN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
port_open() {
  (2>/dev/null >/dev/tcp/localhost/"$1") && return 0 || return 1
}

http_ping() {
  curl -sf --max-time 2 "$1" 2>/dev/null
}

# ── Per-service check ─────────────────────────────────────────────────────────
# check_service <label> <pid-basename> <port> [<ping-url>]
ALL_OK=true

check_service() {
  local label="$1"
  local pid_name="$2"
  local port="$3"
  local ping_url="${4:-}"
  local pid_file="$PID_DIR/${pid_name}.pid"

  echo -e "  ${BOLD}${label}${NC}"

  # ── Process ──────────────────────────────────────────────────────────────
  if [[ ! -f "$pid_file" ]]; then
    echo -e "    Process  : ${RED}DOWN${NC}   (no PID file — service not started)"
    ALL_OK=false
  else
    local pid
    pid=$(cat "$pid_file")
    if kill -0 "$pid" 2>/dev/null; then
      echo -e "    Process  : ${GRN}UP${NC}     (PID $pid)"
    else
      echo -e "    Process  : ${YLW}STALE${NC}  (PID $pid no longer exists — run stop.sh then start.sh)"
      ALL_OK=false
    fi
  fi

  # ── Port ─────────────────────────────────────────────────────────────────
  if port_open "$port"; then
    echo -e "    Port     : ${GRN}OPEN${NC}   (:${CYN}${port}${NC})"
  else
    echo -e "    Port     : ${RED}CLOSED${NC} (:${CYN}${port}${NC})"
    ALL_OK=false
  fi

  # ── HTTP health (APIs only) ───────────────────────────────────────────────
  if [[ -n "$ping_url" ]]; then
    local body
    if body=$(http_ping "$ping_url"); then
      echo -e "    HTTP     : ${GRN}OK${NC}     (GET /ping → ${body})"
    else
      echo -e "    HTTP     : ${RED}FAIL${NC}   (GET /ping did not respond)"
      ALL_OK=false
    fi
  fi

  echo ""
}

# ── Header ────────────────────────────────────────────────────────────────────
echo ""
echo "=== Neural — Service Status =============================================="
echo ""

check_service "Claims API"       "claims-api"       "$CLAIMS_API_PORT"       "http://localhost:${CLAIMS_API_PORT}/ping"
check_service "Underwriting API" "underwriting-api" "$UNDERWRITING_API_PORT" "http://localhost:${UNDERWRITING_API_PORT}/ping"
check_service "Loan API"         "loan-api"         "$LOAN_API_PORT"         "http://localhost:${LOAN_API_PORT}/ping"
check_service "Frontend (Vite)"  "frontend"         "$FRONTEND_PORT"

# ── Summary ───────────────────────────────────────────────────────────────────
echo "=========================================================================="
if [[ "$ALL_OK" == true ]]; then
  echo -e "  ${GRN}${BOLD}All services are up and healthy.${NC}"
else
  echo -e "  ${RED}${BOLD}One or more services are down or unhealthy.${NC}"
  echo -e "  Run ${BOLD}./scripts/start.sh${NC} to start missing services."
fi
echo ""
