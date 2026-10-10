#!/usr/bin/env bash
# Run the 2-minute stress test for one configuration at the VU levels given (manual mode, default),
# or search for its capacity automatically (--search).
#
# Usage: scripts/run_test.sh <tag> <vus...>            run exactly these levels, in order, each one regardless of failures
#        scripts/run_test.sh --search <tag> [vus...]   climb the ladder (default VU_LADDER), then bisect
#   e.g. scripts/run_test.sh node-express-v02-pool 100 150 200
#
# Levels already run for the tag are kept; re-running a level overwrites it. Capacity = highest passing level
# across all levels run for the tag.
#
# For each VU level:
#   1. server: stop app, fresh DB clone, restart Postgres, drop caches, start app  (prepare_run.sh)
#   2. server: start 1s resource sampler in the background                         (collect_metrics.sh)
#   3. local:  k6 ramp 0->VUS in 60s, hold 60s                                      (loadtest/stress.js)
#   4. local:  summarize, judge pass/fail, upsert README row + results/results.csv (summarize.py)
#
# Pass = steady p50 < PASS_P50_MS, p95 < PASS_P95_MS, p99 < PASS_P99_MS and whole-run error % < PASS_ERROR_PCT.
# --search: climb the ladder until a level fails, then bisect (lo=last pass or 0, hi=first fail),
# rounding to SEARCH_STEP (10) VUs, until hi - lo <= SEARCH_STEP.
source "$(dirname "$0")/lib.sh"

SEARCH=0
[[ "${1:-}" == "--search" ]] && { SEARCH=1; shift; }
TAG="${1:?usage: run_test.sh [--search] <tag> <vus...>}"; shift
VUS_LIST=("$@")
if [[ ${#VUS_LIST[@]} -eq 0 ]]; then
  [[ $SEARCH == 1 ]] || { echo "usage: run_test.sh <tag> <vus...>   (VU levels are required; or use --search)"; exit 1; }
  read -r -a VUS_LIST <<< "${VU_LADDER:-100 250 500 1000 2000}"
fi
for v in "${VUS_LIST[@]}"; do [[ "$v" =~ ^[1-9][0-9]*$ ]] || { echo "invalid VU level: $v"; exit 1; }; done
RAMP_S="${RAMP_S:-60}"; HOLD_S="${HOLD_S:-60}"
PASS_P50_MS="${PASS_P50_MS:-500}"
PASS_P95_MS="${PASS_P95_MS:-800}"
PASS_P99_MS="${PASS_P99_MS:-1000}"
PASS_ERROR_PCT="${PASS_ERROR_PCT:-1}"
SEARCH_STEP="${SEARCH_STEP:-10}"
TAG_DIR="$REPO_ROOT/results/$TAG"
META="$REPO_ROOT/data/meta.json"
CRITERIA=(--p50 "$PASS_P50_MS" --p95 "$PASS_P95_MS" --p99 "$PASS_P99_MS" --error-pct "$PASS_ERROR_PCT")

command -v k6 >/dev/null || { echo "k6 not installed (brew install k6)"; exit 1; }
[[ -f "$META" ]] || { echo "data/meta.json missing — run scripts/seed_db.sh first"; exit 1; }
meta() { python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$META" "$1"; }

mkdir -p "$TAG_DIR"
if [[ ! -f "$TAG_DIR/config.md" ]]; then
  cp "$REPO_ROOT/results/CONFIG_TEMPLATE.md" "$TAG_DIR/config.md"
  sed -i '' "s/{{TAG}}/$TAG/" "$TAG_DIR/config.md" 2>/dev/null || sed -i "s/{{TAG}}/$TAG/" "$TAG_DIR/config.md"
  log "Created results/$TAG/config.md — fill in what changed in this configuration."
fi

# k6 holds ~1 socket per VU; the load generator must not be the bottleneck.
ulimit -n 65535 2>/dev/null || ulimit -n "$(ulimit -Hn)" 2>/dev/null || true
LOADGEN_NOFILE="$(ulimit -n)"
(( LOADGEN_NOFILE >= 4096 )) || log "WARNING: ulimit -n is $LOADGEN_NOFILE — high VU levels will fail on the load generator"

STACK="$(remote cat /opt/bench/CURRENT_APP 2>/dev/null || echo unknown)"
remote cat /opt/bench/app/bench.json > "$TAG_DIR/bench.json" 2>/dev/null || echo '{}' > "$TAG_DIR/bench.json"

# Runs one level and sets LAST_PASS=1|0.
run_level() {
  local VUS="$1" RUN_DIR="$TAG_DIR/vus-$1"
  rm -rf "$RUN_DIR"; mkdir -p "$RUN_DIR"
  log "[$TAG] $VUS VUs — preparing server"
  remote_script "$REPO_ROOT/scripts/server/prepare_run.sh" "$DB_USER" "$APP_PORT" > "$RUN_DIR/server_env.txt"

  log "[$TAG] $VUS VUs — starting sampler"
  remote_script "$REPO_ROOT/scripts/server/collect_metrics.sh" "$((RAMP_S + HOLD_S + 20))" "$APP_PORT" \
    > "$RUN_DIR/server_metrics.csv" &
  local SAMPLER_PID=$!
  sleep 3

  local K6_STARTED_AT; K6_STARTED_AT=$(date +%s)
  log "[$TAG] $VUS VUs — k6 running (${RAMP_S}s ramp + ${HOLD_S}s hold)"
  K6_WEB_DASHBOARD=true K6_WEB_DASHBOARD_EXPORT="$RUN_DIR/k6_report.html" K6_WEB_DASHBOARD_PORT=-1 \
  k6 run --quiet \
    -e BASE_URL="$BASE_URL" -e VUS="$VUS" -e RAMP_S="$RAMP_S" -e HOLD_S="$HOLD_S" -e OUT_DIR="$RUN_DIR" \
    -e USER_COUNT="$(meta USER_COUNT)" -e AUTHOR_COUNT="$(meta AUTHOR_COUNT)" -e POST_COUNT="$(meta POST_COUNT)" \
    "$REPO_ROOT/loadtest/stress.js" > "$RUN_DIR/k6_stdout.txt" 2>&1 || true

  wait "$SAMPLER_PID" || true
  remote "journalctl -u bench-app --since '-3min' --no-pager | tail -200" > "$RUN_DIR/app_log_tail.txt" 2>&1 || true
  cp "$TAG_DIR/bench.json" "$RUN_DIR/bench.json"

  cat > "$RUN_DIR/run.json" <<EOF
{
  "tag": "$TAG",
  "stack": "$STACK",
  "vus": $VUS,
  "ramp_s": $RAMP_S,
  "hold_s": $HOLD_S,
  "k6_started_at": $K6_STARTED_AT,
  "loadgen": "$LOADGEN_LABEL",
  "loadgen_nofile": "$LOADGEN_NOFILE",
  "git_sha": "$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo none)",
  "k6_version": "$(k6 version | head -1)",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

  local OUT
  OUT="$(python3 -I "$REPO_ROOT/scripts/summarize.py" "$RUN_DIR" "${CRITERIA[@]}" \
         --readme "$REPO_ROOT/README.md" --csv "$REPO_ROOT/results/results.csv")"
  echo "$OUT"
  LAST_PASS="$(echo "$OUT" | awk -F= '/^pass=/{print $2}')"
  log "[$TAG] $VUS VUs — $([[ "$LAST_PASS" == 1 ]] && echo PASS || echo "FAIL ($(echo "$OUT" | sed -n 's/^fail_reasons=//p'))")"
}

if [[ $SEARCH == 0 ]]; then
  # Manual: run every requested level.
  for VUS in "${VUS_LIST[@]}"; do run_level "$VUS"; done
fi

# --search 1. climb
LO=0; HI=""
[[ $SEARCH == 1 ]] && for VUS in "${VUS_LIST[@]}"; do
  run_level "$VUS"
  if [[ "$LAST_PASS" == 1 ]]; then LO=$VUS; else HI=$VUS; break; fi
done

# --search 2. bisect between last pass and first fail
if [[ $SEARCH == 1 && -n "$HI" ]]; then
  while (( HI - LO > SEARCH_STEP )); do
    MID=$(( ( (LO + HI) / 2 + SEARCH_STEP / 2 ) / SEARCH_STEP * SEARCH_STEP ))
    (( MID <= LO || MID >= HI )) && break
    run_level "$MID"
    if [[ "$LAST_PASS" == 1 ]]; then LO=$MID; else HI=$MID; fi
  done
fi

CAP="$(python3 -I "$REPO_ROOT/scripts/summarize.py" --capacity "$TAG_DIR" "${CRITERIA[@]}" --readme "$REPO_ROOT/README.md")"
echo "$CAP"
log "Done. $CAP — fill results/$TAG/config.md, then: scripts/release.sh $TAG"
