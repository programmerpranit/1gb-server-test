#!/usr/bin/env bash
# Sample server resource usage once per second and print CSV to stdout. Runs ON THE SERVER as root.
# Memory is PSS (proportional set size) summed over each systemd unit's cgroup, so Postgres
# shared_buffers is not double-counted across backends. CPU % is relative to ONE vCPU.
# A single long-lived python3 process reads /proc directly: forking tools every second
# cost ~10% of the droplet's only vCPU.
#
# Usage: collect_metrics.sh <duration_seconds> <app_port>
set -euo pipefail
DURATION="${1:?duration}"
APP_PORT="${2:?app_port}"
APP_UNIT=bench-app.service
PG_UNIT=$(systemctl list-units --type=service --state=running --no-legend 'postgresql@*' | awk '{print $1}' | head -1)
APP_CG="/sys/fs/cgroup$(systemctl show -p ControlGroup --value "$APP_UNIT")"
PG_CG="/sys/fs/cgroup$(systemctl show -p ControlGroup --value "$PG_UNIT")"

exec python3 -I - "$DURATION" "$APP_PORT" "$APP_CG" "$PG_CG" <<'PY'
import sys, time

duration, port, app_cg, pg_cg = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3], sys.argv[4]
port_hex = f"{port:04X}"

def read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""

def cpu_times():
    f = read("/proc/stat").split("\n", 1)[0].split()[1:9]
    return [int(x) for x in f]  # user nice system idle iowait irq softirq steal

def cg_usec(cg):
    for line in read(f"{cg}/cpu.stat").splitlines():
        if line.startswith("usage_usec"):
            return int(line.split()[1])
    return 0

def pss_mb(cg):
    total = 0
    for pid in read(f"{cg}/cgroup.procs").split():
        for line in read(f"/proc/{pid}/smaps_rollup").splitlines():
            if line.startswith("Pss:"):
                total += int(line.split()[1])
                break
    return total // 1024

def meminfo():
    m = {}
    for line in read("/proc/meminfo").splitlines():
        k, v = line.split(":", 1)
        m[k] = int(v.split()[0]) // 1024
    return m

def established_conns():
    n = 0
    for path in ("/proc/net/tcp", "/proc/net/tcp6"):
        for line in read(path).splitlines()[1:]:
            parts = line.split()
            if parts[3] == "01" and parts[1].rsplit(":", 1)[1] == port_hex:
                n += 1
    return n

print("ts,elapsed_s,cpu_total_pct,cpu_user_pct,cpu_sys_pct,cpu_iowait_pct,cpu_steal_pct,app_cpu_pct,"
      "pg_cpu_pct,mem_used_mb,mem_avail_mb,swap_used_mb,app_pss_mb,pg_pss_mb,app_conns,load1", flush=True)

start = time.time()
prev_cpu, prev_app, prev_pg, prev_t = cpu_times(), cg_usec(app_cg), cg_usec(pg_cg), time.monotonic()
tick = start
while time.time() - start < duration:
    tick += 1
    time.sleep(max(0, tick - time.time()))
    cpu, app, pg, t = cpu_times(), cg_usec(app_cg), cg_usec(pg_cg), time.monotonic()
    d = [c - p for c, p in zip(cpu, prev_cpu)]
    tot = sum(d) or 1
    u, n, s, i, w, q, sq, st = d
    wall_us = (t - prev_t) * 1e6 or 1
    m = meminfo()
    print(f"{int(time.time())},{int(time.time() - start)},"
          f"{100 * (tot - i - w) / tot:.1f},{100 * (u + n) / tot:.1f},{100 * (s + q + sq) / tot:.1f},"
          f"{100 * w / tot:.1f},{100 * st / tot:.1f},"
          f"{100 * (app - prev_app) / wall_us:.1f},{100 * (pg - prev_pg) / wall_us:.1f},"
          f"{m['MemTotal'] - m['MemAvailable']},{m['MemAvailable']},{m['SwapTotal'] - m['SwapFree']},"
          f"{pss_mb(app_cg)},{pss_mb(pg_cg)},{established_conns()},"
          f"{read('/proc/loadavg').split()[0]}", flush=True)
    prev_cpu, prev_app, prev_pg, prev_t = cpu, app, pg, t
PY
