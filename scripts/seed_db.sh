#!/usr/bin/env bash
# Convert the xlsx (if needed), upload CSVs + schema, build the `bench_seed` template DB.
# Re-run whenever db/schema.sql or the converter changes.
# Usage: scripts/seed_db.sh
source "$(dirname "$0")/lib.sh"

if [[ ! -f "$REPO_ROOT/data/posts.csv" ]]; then
  log "Converting Twitterdatainsheets.xlsx -> data/"
  python3 -I "$REPO_ROOT/scripts/xlsx_to_csv.py" "$REPO_ROOT/Twitterdatainsheets.xlsx" "$REPO_ROOT/data"
fi

log "Uploading seed files"
rsync -az -e "$SSH_CMD" "$REPO_ROOT"/data/{users,locations,posts}.csv "$REPO_ROOT/db/schema.sql" \
  "$SSH_TARGET:/opt/bench/seed/"

log "Building bench_seed"
remote_script "$REPO_ROOT/scripts/server/seed.sh" "$DB_USER"
remote_script "$REPO_ROOT/scripts/server/reset_db.sh" "$DB_USER"
log "Seeded. Counts for the load test are in data/meta.json"
