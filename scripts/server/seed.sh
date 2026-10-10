#!/usr/bin/env bash
# Build the `bench_seed` template database from /opt/bench/seed/*. Runs ON THE SERVER as root.
# Every test run clones it (scripts/server/reset_db.sh), so all runs start from identical data.
#
# Usage: seed.sh <db_user>
set -euo pipefail
DB_USER="${1:?db_user}"
SEED=/opt/bench/seed
chmod 755 "$SEED"; chmod 644 "$SEED"/*

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DROP DATABASE IF EXISTS bench WITH (FORCE);
UPDATE pg_database SET datistemplate = false WHERE datname = 'bench_seed';
DROP DATABASE IF EXISTS bench_seed WITH (FORCE);
CREATE DATABASE bench_seed OWNER $DB_USER;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d bench_seed <<SQL
SET ROLE $DB_USER;
\i $SEED/schema.sql
\copy locations FROM '$SEED/locations.csv' WITH (FORMAT csv, HEADER true)
\copy users (id, handle, gender) FROM '$SEED/users.csv' WITH (FORMAT csv, HEADER true)
\copy posts (id, external_id, user_id, location_id, text, lang, is_reshare, reach, retweet_count, like_count, klout, sentiment, created_at) FROM '$SEED/posts.csv' WITH (FORMAT csv, HEADER true)
SELECT setval(pg_get_serial_sequence('users', 'id'), (SELECT max(id) FROM users));
SELECT setval(pg_get_serial_sequence('posts', 'id'), (SELECT max(id) FROM posts));
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d bench_seed -c "VACUUM (ANALYZE, FREEZE)"

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
ALTER DATABASE bench_seed IS_TEMPLATE true;
ALTER DATABASE bench_seed ALLOW_CONNECTIONS false;
SQL

sudo -u postgres psql -tA -c "SELECT pg_size_pretty(pg_database_size('bench_seed'))" | sed 's/^/bench_seed size: /'
