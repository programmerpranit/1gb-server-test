#!/usr/bin/env bash
# Put the server in an identical cold state before every test run. Runs ON THE SERVER as root.
#   stop app -> fresh DB clone -> restart Postgres -> drop page cache -> start app (+ nginx if enabled) -> wait healthy
# Prints a short environment snapshot (recorded in results/<tag>/vus-<n>/server_env.txt).
#
# Usage: prepare_run.sh <db_user> <app_port>
set -euo pipefail
DB_USER="${1:?db_user}"
APP_PORT="${2:?app_port}"

systemctl stop bench-app
sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
DROP DATABASE IF EXISTS bench WITH (FORCE);
CREATE DATABASE bench TEMPLATE bench_seed OWNER $DB_USER;
SQL
systemctl restart postgresql
sync; echo 3 > /proc/sys/vm/drop_caches
systemctl start bench-app
if systemctl is-enabled --quiet nginx 2>/dev/null; then systemctl restart nginx; fi

for _ in $(seq 1 30); do
  curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null 2>&1 && break
  sleep 1
done
curl -fsS "http://127.0.0.1:$APP_PORT/health" >/dev/null

echo "app=$(cat /opt/bench/CURRENT_APP 2>/dev/null || echo unknown)"
echo "kernel=$(uname -r)"
echo "os=$(. /etc/os-release && echo "$PRETTY_NAME")"
echo "nproc=$(nproc)"
echo "mem_total_mb=$(free -m | awk '/Mem/{print $2}')"
echo "node=$(node -v 2>/dev/null || echo none)"
echo "python=$(python3 --version 2>/dev/null | awk '{print $2}')"
echo "go=$(go version 2>/dev/null | awk '{print $3}' || true)"
echo "postgres=$(psql --version | awk '{print $3}')"
echo "proxy=$(systemctl is-active --quiet nginx && nginx -v 2>&1 | awk -F': ' '{print $2}' || echo none)"
echo "swap_mb=$(free -m | awk '/Swap/{print $2}')"
echo "shared_buffers=$(sudo -u postgres psql -tAc 'SHOW shared_buffers')"
echo "max_connections=$(sudo -u postgres psql -tAc 'SHOW max_connections')"
echo "mem_avail_mb_idle=$(free -m | awk '/Mem/{print $7}')"
