#!/usr/bin/env bash
# Upload apps/<name>/ to the server, build it, (re)start the bench-app service.
# Usage: scripts/deploy.sh <app_name>      e.g. scripts/deploy.sh node-express
source "$(dirname "$0")/lib.sh"
APP_NAME="${1:?usage: deploy.sh <app_name>}"
APP_SRC="$REPO_ROOT/apps/$APP_NAME"
[[ -f "$APP_SRC/start.sh" ]] || { echo "apps/$APP_NAME/start.sh missing (see CLAUDE.md app contract)"; exit 1; }

log "Uploading apps/$APP_NAME"
rsync -az -e "$SSH_CMD" --delete \
  --exclude node_modules --exclude target --exclude .venv --exclude __pycache__ \
  "$APP_SRC/" "$SSH_TARGET:/opt/bench/app/"

log "Building + restarting"
remote_script "$REPO_ROOT/scripts/server/install_app.sh" "$APP_NAME"

log "Health check"
for _ in $(seq 1 30); do
  if curl -fsS "$BASE_URL/health" >/dev/null; then log "Up: $BASE_URL"; exit 0; fi
  sleep 1
done
echo "App did not become healthy at $BASE_URL/health" >&2
exit 1
