#!/usr/bin/env bash
# Recreate the `bench` database as a fresh clone of `bench_seed`. Runs ON THE SERVER as root.
# Usage: reset_db.sh <db_user>
set -euo pipefail
DB_USER="${1:?db_user}"

sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
DROP DATABASE IF EXISTS bench WITH (FORCE);
CREATE DATABASE bench TEMPLATE bench_seed OWNER $DB_USER;
SQL
echo "bench reset from bench_seed"
