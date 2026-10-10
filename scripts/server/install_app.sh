#!/usr/bin/env bash
# Build the uploaded app in /opt/bench/app and (re)install the bench-app systemd unit.
# Runs ON THE SERVER as root. Language-agnostic: relies on the app's build.sh / start.sh.
#
# Usage: install_app.sh <app_name>
set -euo pipefail
APP_NAME="${1:?app_name}"
APP_DIR=/opt/bench/app

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
ExecStart=$APP_DIR/start.sh
Restart=always
RestartSec=1
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

echo "$APP_NAME" > /opt/bench/CURRENT_APP
systemctl daemon-reload
systemctl enable bench-app >/dev/null 2>&1
systemctl restart bench-app
sleep 2
systemctl --no-pager --lines=5 status bench-app
