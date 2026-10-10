#!/usr/bin/env bash
# Profiling run — NOT an official test. Answers "where does the CPU go at this load?" for the deployed app.
#   1. fresh state (prepare_run.sh), app restarted under a profiler
#   2. k6 from the load generator at <vus> (same stress.js, 60 s ramp + 60 s hold)
#   3. during the hold: `perf record` system-wide on the target (Postgres, kernel, app)
#   4. Node apps also get V8's --cpu-prof (JS functions, GC) and --perf-basic-prof (JIT names for perf)
# Writes text reports to profiles/<date>-<label>/ (raw profiles stay in /tmp on the droplet).
# Profilers add overhead, so throughput/latency from this run are not comparable with official runs.
#
# Usage: scripts/profile.sh <vus> [label]
source "$(dirname "$0")/lib.sh"
: "${LOADGEN_HOST:?profiling needs the load generator (LOADGEN_HOST)}"
VUS="${1:?usage: profile.sh <vus> [label]}"
RAMP_S="${RAMP_S:-60}"; HOLD_S="${HOLD_S:-60}"
PERF_S="${PERF_S:-40}"   # perf samples this long, starting 10 s into the hold
STACK="$(remote cat /opt/bench/CURRENT_APP)"
LABEL="${2:-$STACK-$VUS}"
OUT="$REPO_ROOT/profiles/$(date +%Y-%m-%d)-$LABEL"
mkdir -p "$OUT"
meta() { python3 -I -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$REPO_ROOT/data/meta.json" "$1"; }

log "Profiling $STACK at $VUS VUs -> ${OUT#$REPO_ROOT/}"
remote_script "$REPO_ROOT/scripts/server/prepare_run.sh" "$DB_USER" "$APP_PORT" > "$OUT/server_env.txt"
remote_script "$REPO_ROOT/scripts/server/cpu_probe.sh" before >> "$OUT/server_env.txt" || true

# Whatever happens, leave the normal service running afterwards.
trap 'remote "systemctl stop bench-prof 2>/dev/null; systemctl reset-failed bench-prof 2>/dev/null; systemctl start bench-app" || true' EXIT
# Restart the app as a transient unit with the same user/env/limits as bench-app, plus Node profiler flags.
remote "systemctl stop bench-app; rm -rf /tmp/bench-prof; mkdir -p /tmp/bench-prof; chown bench /tmp/bench-prof
  systemd-run --quiet --unit=bench-prof --uid=bench -p LimitNOFILE=65535 -p WorkingDirectory=/opt/bench/app \
    -p EnvironmentFile=/opt/bench/app.env \
    -E 'NODE_OPTIONS=--cpu-prof --cpu-prof-dir=/tmp/bench-prof --perf-basic-prof' /opt/bench/app/start.sh
  for _ in \$(seq 1 30); do curl -fsS http://127.0.0.1:$APP_PORT/health >/dev/null 2>&1 && exit 0; sleep 1; done; exit 1"

RDIR="/opt/loadgen/runs/profile-$LABEL"
loadgen "rm -rf '$RDIR' && mkdir -p '$RDIR'"
scp -q "${SSH_OPTS[@]}" "$REPO_ROOT/loadtest/stress.js" "$LOADGEN_TARGET:$RDIR/stress.js"
log "k6 running (${RAMP_S}s ramp + ${HOLD_S}s hold); perf records ${PERF_S}s from $((RAMP_S + 10))s"
( sleep $((RAMP_S + 10))
  remote "perf record -F 499 -a -g -o /tmp/bench-prof/perf.data -- sleep $PERF_S" > "$OUT/perf_record.log" 2>&1
) &
PERF_PID=$!
loadgen "cd '$RDIR' && ulimit -n 1048576 && k6 run --quiet -e BASE_URL=$BASE_URL -e VUS=$VUS -e RAMP_S=$RAMP_S \
  -e HOLD_S=$HOLD_S -e USER_COUNT=$(meta USER_COUNT) -e AUTHOR_COUNT=$(meta AUTHOR_COUNT) \
  -e POST_COUNT=$(meta POST_COUNT) -e OUT_DIR='$RDIR' stress.js" > "$OUT/k6_stdout.txt" 2>&1 || true
wait "$PERF_PID" || true
scp -q "${SSH_OPTS[@]}" "$LOADGEN_TARGET:$RDIR/k6_summary.json" "$OUT/k6_summary.json" || true

log "Stopping the profiled app (writes the V8 profile) and restoring bench-app"
remote "systemctl stop bench-prof; sleep 1; systemctl reset-failed bench-prof 2>/dev/null; systemctl start bench-app"

log "perf reports"
# By process (comm), by process + binary (dso), then the hottest symbols overall and per process.
remote "cd /tmp/bench-prof && R='perf report -i perf.data --stdio --no-children --percent-limit 0.5'
  \$R --sort comm 2>/dev/null | grep -v '^#' | sed '/^$/d' > by_process.txt
  \$R --sort comm,dso 2>/dev/null | grep -v '^#' | sed '/^$/d' > by_process_dso.txt
  \$R -g none --sort comm,dso,sym 2>/dev/null | grep -v '^#' | sed '/^$/d' | head -80 > top_symbols.txt
  \$R -g none --comms postgres --sort sym 2>/dev/null | grep -v '^#' | sed '/^$/d' | head -50 > postgres_symbols.txt
  \$R -g none --comms node --sort sym 2>/dev/null | grep -v '^#' | sed '/^$/d' | head -50 > node_symbols.txt"
for f in by_process.txt by_process_dso.txt top_symbols.txt postgres_symbols.txt node_symbols.txt; do
  scp -q "${SSH_OPTS[@]}" "$SSH_TARGET:/tmp/bench-prof/$f" "$OUT/perf_$f" || true
done

# Node only: summarise the V8 CPU profile (self time by function and by category).
PROF="$(remote "ls -t /tmp/bench-prof/*.cpuprofile 2>/dev/null | head -1")"
if [[ -n "$PROF" ]]; then
  scp -q "${SSH_OPTS[@]}" "$SSH_TARGET:$PROF" "$OUT/node.cpuprofile"
  python3 -I "$REPO_ROOT/scripts/cpuprofile_summary.py" "$OUT/node.cpuprofile" > "$OUT/node_cpuprofile.txt"
  gzip -f "$OUT/node.cpuprofile"
fi
log "Done: ${OUT#$REPO_ROOT/}"
