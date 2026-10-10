#!/usr/bin/env bash
# Sample load-generator resource usage once per second; CSV to stdout. Runs ON THE LOAD GENERATOR.
# Shows whether k6 itself became a bottleneck (CPU % is relative to ALL vCPUs of the load generator).
#
# Usage: loadgen_metrics.sh <duration_seconds>
set -euo pipefail
DURATION="${1:?duration}"

exec python3 -I - "$DURATION" <<'PY'
import os, sys, time

duration = int(sys.argv[1])
ticks = os.sysconf("SC_CLK_TCK")

def read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""

def cpu_times():
    f = [int(x) for x in read("/proc/stat").split("\n", 1)[0].split()[1:9]]
    return sum(f), f[3] + f[4]  # total, idle+iowait

def k6_stats():
    cpu, rss = 0, 0
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or read(f"/proc/{pid}/comm").strip() != "k6":
            continue
        stat = read(f"/proc/{pid}/stat").rsplit(")", 1)[-1].split()
        if len(stat) > 13:
            cpu += int(stat[11]) + int(stat[12])  # utime + stime
        for line in read(f"/proc/{pid}/status").splitlines():
            if line.startswith("VmRSS:"):
                rss += int(line.split()[1])
    return cpu, rss // 1024

def mem():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) // 1024
    return m["MemTotal"] - m["MemAvailable"]

print("ts,elapsed_s,lg_cpu_pct,k6_cpu_pct,k6_rss_mb,lg_mem_used_mb", flush=True)
ncpu = os.cpu_count() or 1
start = time.time()
prev_tot, prev_idle = cpu_times()
prev_k6, _ = k6_stats()
prev_t = time.monotonic()
tick = start
while time.time() - start < duration:
    tick += 1
    time.sleep(max(0, tick - time.time()))
    tot, idle = cpu_times()
    k6cpu, k6rss = k6_stats()
    t = time.monotonic()
    dt = (tot - prev_tot) or 1
    k6_pct = 100 * max(0, k6cpu - prev_k6) / ticks / ((t - prev_t) * ncpu)
    print(f"{int(time.time())},{int(time.time() - start)},{100 * (dt - (idle - prev_idle)) / dt:.1f},"
          f"{k6_pct:.1f},{k6rss},{mem()}", flush=True)
    prev_tot, prev_idle, prev_k6, prev_t = tot, idle, k6cpu, t
PY
