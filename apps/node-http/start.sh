#!/usr/bin/env bash
# systemd ExecStart. PORT, DATABASE_URL and NODE_ENV come from /opt/bench/app.env.
exec node src/server.js
