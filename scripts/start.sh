#!/usr/bin/env bash
# start.sh — Start all Neural services (3 FastAPI agents + Vite frontend)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$REPO_ROOT/scripts/pids"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$PID_DIR" "$LOG_DIR"

# ── Load environment ──────────────────────────────────────────────────────────
if [[ -f "$REPO_ROOT/.env" ]]; then
  set -o allexport
  source "$REPO_ROOT/.env"
  set +o allexport
else
  echo "⚠  No .env file found at $REPO_ROOT/.env — using defaults"
fi

CLAIMS_API_PORT="${CLAIMS_API_PORT:-8001}"
UNDERWRITING_API_PORT="${UNDERWRITING_API_PORT:-8002}"
LOAN_API_PORT="${LOAN_API_PORT:-8003}"

# ── Activate virtualenv if present ───────────────────────────────────────────
if [[ -f "$REPO_ROOT/.venv/Scripts/activate" ]]; then
  source "$REPO_ROOT/.venv/Scripts/activate"
elif [[ -f "$REPO_ROOT/.venv/bin/activate" ]]; then
  source "$REPO_ROOT/.venv/bin/activate"
elif [[ -f "$REPO_ROOT/venv/Scripts/activate" ]]; then
  source "$REPO_ROOT/venv/Scripts/activate"
elif [[ -f "$REPO_ROOT/venv/bin/activate" ]]; then
  source "$REPO_ROOT/venv/bin/activate"
fi

# ── Helper: start one FastAPI service ────────────────────────────────────────
start_api() {
  local name="$1"        # e.g. "claims"
  local port="$2"        # e.g. 8001
  local pid_file="$PID_DIR/${name}-api.pid"
  local log_file="$LOG_DIR/${name}-api.log"

  if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "  [skip] $name API already running (PID $(cat "$pid_file"))"
    return
  fi

  echo "  Starting $name API on :$port …"
  (
    cd "$REPO_ROOT"
    uvicorn "agents.${name}.apis.main:app" --host 0.0.0.0 --port "$port" 2>&1 | tee "$log_file"
  ) &
  echo $! > "$pid_file"
  echo "  ✓  $name API  →  http://localhost:$port  (log: logs/${name}-api.log)"
}

# ── Start backend services ────────────────────────────────────────────────────
echo ""
echo "=== Neural — Starting services ==="
echo ""
start_api "claims"       "$CLAIMS_API_PORT"
start_api "underwriting" "$UNDERWRITING_API_PORT"
start_api "loan"         "$LOAN_API_PORT"

# ── Start Vite frontend ───────────────────────────────────────────────────────
FRONTEND_DIR="$REPO_ROOT/frontend"
FRONTEND_PID="$PID_DIR/frontend.pid"
FRONTEND_LOG="$LOG_DIR/frontend.log"

if [[ -f "$FRONTEND_PID" ]] && kill -0 "$(cat "$FRONTEND_PID")" 2>/dev/null; then
  echo "  [skip] Frontend already running (PID $(cat "$FRONTEND_PID"))"
else
  if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo "  Installing frontend dependencies …"
    (cd "$FRONTEND_DIR" && npm install >> "$FRONTEND_LOG" 2>&1)
  fi
  echo "  Starting Vite frontend …"
  (cd "$FRONTEND_DIR" && npm run dev 2>&1 | tee "$FRONTEND_LOG") &
  echo $! > "$FRONTEND_PID"
  echo "  ✓  Frontend  →  http://localhost:5173  (log: logs/frontend.log)"
fi

echo ""
echo "=== All services started. Streaming logs below (Ctrl+C exits logs; services keep running). ==="
echo "=== Run ./scripts/stop.sh to stop all services. ==="
echo ""

# Stream all logs to the console
wait
