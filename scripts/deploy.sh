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

# Checked on the droplet itself: BASE_URL may be the private IP, which only the load generator can reach.
log "Health check"
if remote "for _ in \$(seq 1 30); do curl -fsS http://127.0.0.1:$APP_PORT/health >/dev/null && exit 0; sleep 1; done; exit 1"; then
  log "Up on the droplet (load tests use $BASE_URL)"; exit 0
fi
echo "App did not become healthy at 127.0.0.1:$APP_PORT/health on the droplet" >&2
exit 1
