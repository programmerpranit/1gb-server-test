#!/usr/bin/env bash
# systemd ExecStart. PORT, DATABASE_URL and NODE_ENV come from /opt/bench/app.env.
# Runtime: Bun (node-http-v02); the same node:http + pg code runs on Bun's Node compatibility layer.
exec bun src/server.js
