#!/usr/bin/env bash
# Sample server resource usage once per second and print CSV to stdout. Runs ON THE SERVER as root.
# Memory is PSS (proportional set size) summed over each systemd unit's cgroup, so Postgres
# shared_buffers is not double-counted across backends. CPU % is relative to ONE vCPU.
#
# Usage: collect_metrics.sh <duration_seconds> <app_port>
set -euo pipefail
DURATION="${1:?duration}"
APP_PORT="${2:?app_port}"
APP_UNIT=bench-app.service
PG_UNIT=$(systemctl list-units --type=service --state=running --no-legend 'postgresql@*' | awk '{print $1}' | head -1)

cgroup_dir() { echo "/sys/fs/cgroup$(systemctl show -p ControlGroup --value "$1")"; }
APP_CG=$(cgroup_dir "$APP_UNIT")
PG_CG=$(cgroup_dir "$PG_UNIT")

pss_mb() {
  local total=0 pid v
  for pid in $(cat "$1/cgroup.procs" 2>/dev/null); do
    v=$(awk '/^Pss:/{print $2}' "/proc/$pid/smaps_rollup" 2>/dev/null || true)
    total=$((total + ${v:-0}))
  done
  echo $((total / 1024))
}
cg_cpu_usec() { awk '/^usage_usec/{print $2}' "$1/cpu.stat" 2>/dev/null || echo 0; }
meminfo() { awk -v k="$1:" '$1==k{print int($2/1024)}' /proc/meminfo; }

read_cpu() { read -r _ u n s i w q sq st _ < /proc/stat; echo "$u $n $s $i $w $q $sq $st"; }

echo "ts,elapsed_s,cpu_total_pct,cpu_user_pct,cpu_sys_pct,cpu_iowait_pct,cpu_steal_pct,app_cpu_pct,pg_cpu_pct,mem_used_mb,mem_avail_mb,swap_used_mb,app_pss_mb,pg_pss_mb,app_conns,load1"

start=$(date +%s)
read -r pu pn ps pi pw pq psq pst <<< "$(read_cpu)"
p_app=$(cg_cpu_usec "$APP_CG"); p_pg=$(cg_cpu_usec "$PG_CG"); p_t=$(date +%s%N)

while (( $(date +%s) - start < DURATION )); do
  sleep 1
  read -r u n s i w q sq st <<< "$(read_cpu)"
  c_app=$(cg_cpu_usec "$APP_CG"); c_pg=$(cg_cpu_usec "$PG_CG"); c_t=$(date +%s%N)

  du=$((u-pu)); dn=$((n-pn)); ds=$((s-ps)); di=$((i-pi)); dw=$((w-pw)); dq=$((q-pq)); dsq=$((sq-psq)); dst=$((st-pst))
  tot=$((du+dn+ds+di+dw+dq+dsq+dst)); (( tot > 0 )) || tot=1
  wall_us=$(( (c_t - p_t) / 1000 )); (( wall_us > 0 )) || wall_us=1

  mem_total=$(meminfo MemTotal); mem_avail=$(meminfo MemAvailable)
  swap_total=$(meminfo SwapTotal); swap_free=$(meminfo SwapFree)
  conns=$(ss -Htn state established "( sport = :$APP_PORT )" | wc -l)
  load1=$(cut -d' ' -f1 /proc/loadavg)

  awk -v ts="$(date +%s)" -v el="$(( $(date +%s) - start ))" \
      -v tot="$tot" -v busy="$((tot-di-dw))" -v us="$((du+dn))" -v sy="$((ds+dq+dsq))" -v io="$dw" -v stl="$dst" \
      -v app="$((c_app-p_app))" -v pg="$((c_pg-p_pg))" -v wall="$wall_us" \
      -v used="$((mem_total-mem_avail))" -v avail="$mem_avail" -v swap="$((swap_total-swap_free))" \
      -v apss="$(pss_mb "$APP_CG")" -v ppss="$(pss_mb "$PG_CG")" -v conns="$conns" -v l1="$load1" \
      'BEGIN { printf "%s,%s,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%s,%s,%s,%s,%s,%s,%s\n",
               ts, el, 100*busy/tot, 100*us/tot, 100*sy/tot, 100*io/tot, 100*stl/tot,
               100*app/wall, 100*pg/wall, used, avail, swap, apss, ppss, conns, l1 }'

  pu=$u; pn=$n; ps=$s; pi=$i; pw=$w; pq=$q; psq=$sq; pst=$st
  p_app=$c_app; p_pg=$c_pg; p_t=$c_t
done
