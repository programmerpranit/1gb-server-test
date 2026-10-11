#!/usr/bin/env bash
# Build the uploaded app in /opt/bench/app and (re)install the bench-app systemd unit.
# Runs ON THE SERVER as root. Language-agnostic: relies on the app's build.sh / start.sh.
#
# Optional reverse proxy: if the app ships nginx.conf, it replaces /etc/nginx/nginx.conf, nginx serves the public
# port (APP_PORT, 3000) and the app moves to UPSTREAM_PORT (3001, via app.override.env). Without nginx.conf, nginx
# is stopped and the app serves APP_PORT itself.
#
# Usage: install_app.sh <app_name>
set -euo pipefail
APP_NAME="${1:?app_name}"
APP_DIR=/opt/bench/app
UPSTREAM_PORT=3001

chown -R bench:bench "$APP_DIR"
chmod +x "$APP_DIR"/*.sh

if [[ -x "$APP_DIR/build.sh" ]]; then
  echo ">> build.sh"
  (cd "$APP_DIR" && sudo -u bench -H ./build.sh)
fi

cat > /etc/systemd/system/bench-app.service <<EOF
[Unit]
Description=Benchmark app ($APP_NAME)
After=network.target postgresql.service

[Service]
User=bench
WorkingDirectory=$APP_DIR
EnvironmentFile=/opt/bench/app.env
EnvironmentFile=-/opt/bench/app.override.env
ExecStart=$APP_DIR/start.sh
Restart=always
RestartSec=1
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

if [[ -f "$APP_DIR/nginx.conf" ]]; then
  echo ">> nginx in front (app on 127.0.0.1:$UPSTREAM_PORT)"
  echo "PORT=$UPSTREAM_PORT" > /opt/bench/app.override.env
  [[ -f /etc/nginx/nginx.conf.orig ]] || cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.orig
  cp "$APP_DIR/nginx.conf" /etc/nginx/nginx.conf
  nginx -t
else
  : > /opt/bench/app.override.env
  systemctl disable --now nginx >/dev/null 2>&1 || true
fi
chmod 644 /opt/bench/app.override.env

echo "$APP_NAME" > /opt/bench/CURRENT_APP
systemctl daemon-reload
systemctl enable bench-app >/dev/null 2>&1
systemctl restart bench-app
if [[ -f "$APP_DIR/nginx.conf" ]]; then systemctl enable nginx >/dev/null 2>&1; systemctl restart nginx; fi
sleep 2
systemctl --no-pager --lines=5 status bench-app
