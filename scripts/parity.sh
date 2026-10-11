#!/usr/bin/env bash
# Contract parity check: 39 requests (every endpoint, 400/401/404, invalid JSON, idempotent like/unlike, FK errors)
# against the app on the droplet, on a freshly reset DB. Prints one line per request: status, body (created_at
# masked) and content type. Compare two stacks with diff:
#   scripts/parity.sh > /tmp/a.txt   (deploy stack A first)
#   scripts/parity.sh > /tmp/b.txt   (deploy stack B)      diff /tmp/a.txt /tmp/b.txt
# Only the first line (app name) may differ. Reference output: node-http (v01..v04 were all identical).
source "$(dirname "$0")/lib.sh"
remote_script "$REPO_ROOT/scripts/server/prepare_run.sh" "$DB_USER" "$APP_PORT" >/dev/null
remote "cat /opt/bench/CURRENT_APP"
remote_script "$REPO_ROOT/scripts/server/parity_requests.sh"
