#!/usr/bin/env bash
# stop.sh — Stop all Neural services
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$REPO_ROOT/scripts/pids"

# ── Helper: kill any process listening on a given port ───────────────────────
kill_by_port() {
  local port="$1"
  local pids
  pids=$(netstat -ano 2>/dev/null | grep ":${port}[[:space:]]" | grep LISTENING | awk '{print $NF}' | sort -u || true)
  if [[ -z "$pids" ]]; then
    pids=$(ss -tlnp 2>/dev/null | grep ":${port}[[:space:]]" | grep -oP 'pid=\K[0-9]+' || true)
  fi
  for p in $pids; do
    [[ -z "$p" || "$p" == "0" ]] && continue
    taskkill //PID "$p" //F 2>/dev/null && echo "  ✓  killed PID $p on port $port" || true
  done
}

# ── Helper: stop one service by PID file ─────────────────────────────────────
stop_service() {
  local name="$1"
  local port="${2:-}"
  local pid_file="$PID_DIR/${name}.pid"

  if [[ ! -f "$pid_file" ]]; then
    if [[ -n "$port" ]]; then
      echo "  [fallback] $name — no PID file, checking port $port …"
      kill_by_port "$port"
    else
      echo "  [skip] $name — no PID file found"
    fi
    return
  fi

  local pid
  pid=$(cat "$pid_file")

  if ! kill -0 "$pid" 2>/dev/null; then
    echo "  [skip] $name — process $pid not running"
    rm -f "$pid_file"
    return
  fi

  echo "  Stopping $name (PID $pid) …"
  kill -TERM "$pid" 2>/dev/null || true

  # Wait up to 5 s for graceful shutdown
  local waited=0
  while kill -0 "$pid" 2>/dev/null && [[ $waited -lt 5 ]]; do
    sleep 1
    (( waited++ )) || true
  done

  # Force-kill if still running
  if kill -0 "$pid" 2>/dev/null; then
    echo "  ⚠  $name did not stop gracefully — force killing …"
    kill -KILL "$pid" 2>/dev/null || true
  fi

  rm -f "$pid_file"
  echo "  ✓  $name stopped"
}

echo ""
echo "=== Neural — Stopping services ==="
echo ""

stop_service "claims-api"      8001
stop_service "underwriting-api" 8002
stop_service "loan-api"         8003
stop_service "frontend"         5173

echo ""
echo "=== All services stopped. ==="
echo ""
