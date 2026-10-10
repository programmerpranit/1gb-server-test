#!/usr/bin/env bash
# Keep the live k6 dashboard tunnel open (Ctrl-C to stop): http://localhost:$DASHBOARD_PORT
# k6 serves the dashboard only while a test level is running; refresh the page when a level starts.
# run_test.sh reuses this tunnel when it is already open.
# Usage: scripts/dashboard.sh
source "$(dirname "$0")/lib.sh"
: "${LOADGEN_HOST:?set LOADGEN_HOST in .env}"
log "Dashboard tunnel open: http://localhost:$DASHBOARD_PORT (refresh when a test level starts; Ctrl-C to stop)"
exec ssh "${SSH_OPTS[@]}" -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -N \
  -L "$DASHBOARD_PORT:127.0.0.1:5665" "$LOADGEN_TARGET" 2>/dev/null
