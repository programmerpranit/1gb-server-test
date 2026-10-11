#!/usr/bin/env bash
# Runs on the server as user bench (scripts/server/install_app.sh).
set -euo pipefail
npm ci --omit=dev --no-audit --no-fund
