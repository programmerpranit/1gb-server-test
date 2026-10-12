#!/usr/bin/env bash
# systemd ExecStart. PORT and DATABASE_URL come from /opt/bench/app.env.
# One uvicorn process (no --workers), asyncio event loop + h11 parser, no access log (no request logging, as in
# every other stack).
export PYTHONUNBUFFERED=1
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --loop asyncio --http h11 --no-access-log
