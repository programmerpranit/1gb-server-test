#!/usr/bin/env bash
# Time a fixed single-threaded CPU workload to measure how fast the droplet's shared vCPU is right now.
# Runs ON THE SERVER via `ssh bash -s`, before and after k6 (never during: it would steal CPU from the app).
# A shared vCPU can run ~30 % faster or slower depending on neighbours, without showing up as steal; a higher
# probe time means a slower host. Speed also swings ±20 % within seconds, so the probe reports the median of 15
# runs (≈ 1.5 s). Prints `cpu_probe_<label>_ms=<median>` for server_env.txt.
#
# Usage: cpu_probe.sh <label>      e.g. cpu_probe.sh before
set -euo pipefail
LABEL="${1:?label}"

exec python3 -I - "$LABEL" <<'PY'
import json, statistics, sys, time

# Work shaped like the app's: integer arithmetic plus JSON encode/decode of a feed page (20 posts).
page = {"posts": [{"id": 100000 - i, "user_id": 4000 + i, "handle": f"tw-{1000000 + i}",
                   "text": "RT @someone: a tweet about cloud hosting and databases " * 2, "is_public": True,
                   "like_count": i, "comment_count": i % 3, "created_at": "2016-04-01T12:00:00.000Z"}
                  for i in range(20)], "next_before": 99980}

def work():
    s = 0
    for i in range(400_000):
        s += i * i % 7
    for _ in range(400):
        json.loads(json.dumps(page))
    return s

work()  # warm-up
work()
times = []
for _ in range(15):
    t = time.perf_counter()
    work()
    times.append((time.perf_counter() - t) * 1000)
print(f"cpu_probe_{sys.argv[1]}_ms={statistics.median(times):.1f}")
PY
