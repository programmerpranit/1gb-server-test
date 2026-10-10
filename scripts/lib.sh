# Shared helpers for local scripts. Source it: `source "$(dirname "$0")/lib.sh"`
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$REPO_ROOT/.env" ]]; then
  set -a; source "$REPO_ROOT/.env"; set +a
fi

: "${SERVER_HOST:?set SERVER_HOST in .env}"
SERVER_USER="${SERVER_USER:-root}"
APP_PORT="${APP_PORT:-3000}"
DB_USER="${DB_USER:-bench}"
LOADGEN_LABEL="${LOADGEN_LABEL:-unknown}"
SSH_TARGET="$SERVER_USER@$SERVER_HOST"
SSH_OPTS=(-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10)
[[ -n "${SSH_KEY:-}" ]] && SSH_OPTS+=(-i "${SSH_KEY/#\~/$HOME}" -o IdentitiesOnly=yes)
# For rsync -e
SSH_CMD="ssh ${SSH_OPTS[*]}"
# Host k6 targets. Use the droplet's private VPC IP when the load generator is in the same region.
TARGET_HOST="${TARGET_HOST:-$SERVER_HOST}"
BASE_URL="http://$TARGET_HOST:$APP_PORT"

# Run a local script on the server: remote_script <local_script> [args...]
remote_script() {
  local script="$1"; shift
  ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "bash -s -- $*" < "$script"
}

# Run a command on the server: remote <command string>
remote() {
  ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "$@"
}

log() { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
