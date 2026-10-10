#!/usr/bin/env bash
# One-time: provision the droplet (packages, Node, Postgres role, firewall).
# Usage: scripts/provision.sh
source "$(dirname "$0")/lib.sh"
: "${DB_PASSWORD:?set DB_PASSWORD in .env}"

log "Provisioning $SSH_TARGET"
remote_script "$REPO_ROOT/scripts/server/setup.sh" "$DB_USER" "$DB_PASSWORD" "$APP_PORT"
log "Done. Next: scripts/seed_db.sh"
