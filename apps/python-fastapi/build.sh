#!/usr/bin/env bash
# Runs on the server as user bench (scripts/server/install_app.sh). System Python 3.12 (Ubuntu 24.04) + venv.
set -euo pipefail
[[ -x .venv/bin/python ]] || python3 -m venv .venv
.venv/bin/pip install --no-cache-dir --disable-pip-version-check -q -r requirements.txt
