#!/usr/bin/env bash
# Provision the load-generator droplet (install pinned k6, limits, sysctls). Run once per new load generator.
# Usage: scripts/provision_loadgen.sh
source "$(dirname "$0")/lib.sh"
: "${LOADGEN_HOST:?set LOADGEN_HOST in .env}"
K6_VERSION="${K6_VERSION:-2.3.0}"

log "Provisioning load generator $LOADGEN_TARGET"
loadgen_script "$REPO_ROOT/scripts/server/loadgen_setup.sh" "$K6_VERSION"
log "Checking it reaches the target at $BASE_URL"
loadgen "curl -fsS -o /dev/null -w 'target health %{http_code} in %{time_total}s\n' $BASE_URL/health"
log "Done. Next: scripts/run_test.sh <tag> <vus...>"
