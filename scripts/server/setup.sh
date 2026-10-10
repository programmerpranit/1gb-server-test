#!/usr/bin/env bash
# One-time provisioning of the droplet under test. Runs ON THE SERVER as root.
# Invoked by scripts/provision.sh; safe to re-run.
#
# Usage: setup.sh <db_user> <db_password> <app_port> [node_major]
set -euo pipefail

DB_USER="${1:?db_user}"
DB_PASSWORD="${2:?db_password}"
APP_PORT="${3:?app_port}"
NODE_MAJOR="${4:-24}"

export DEBIAN_FRONTEND=noninteractive

echo ">> base packages"
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg rsync ufw postgresql postgresql-contrib build-essential jq

echo ">> Node.js $NODE_MAJOR (NodeSource)"
if ! command -v node >/dev/null || [[ "$(node -v | cut -d. -f1)" != "v$NODE_MAJOR" ]]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | bash -
  apt-get install -y nodejs
fi

echo ">> timezone + limits"
timedatectl set-timezone UTC
cat > /etc/security/limits.d/bench.conf <<EOF
*    soft nofile 65535
*    hard nofile 65535
EOF
# Larger accept backlog / ephemeral ports. Recorded as part of the baseline environment.
cat > /etc/sysctl.d/90-bench.conf <<EOF
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 4096
net.ipv4.ip_local_port_range = 10240 65535
EOF
sysctl --system >/dev/null

echo ">> app user + dirs"
id bench >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin bench
mkdir -p /opt/bench/app /opt/bench/seed
chown -R bench:bench /opt/bench/app
chmod 755 /opt/bench /opt/bench/seed

echo ">> postgres role (listens on localhost only — Ubuntu default)"
sudo -u postgres psql -v ON_ERROR_STOP=1 -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
  || sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD'"
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER ROLE $DB_USER PASSWORD '$DB_PASSWORD'"

cat > /opt/bench/app.env <<EOF
PORT=$APP_PORT
DATABASE_URL=postgres://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/bench
NODE_ENV=production
EOF
chmod 640 /opt/bench/app.env
chown root:bench /opt/bench/app.env

echo ">> firewall"
ufw allow OpenSSH
ufw allow "$APP_PORT/tcp"
ufw --force enable

echo ">> swap (baseline = OFF; DigitalOcean droplets ship without swap)"
swapon --show || true

echo ">> versions"
uname -r
lsb_release -ds 2>/dev/null || cat /etc/os-release | head -1
node -v
psql --version
nproc
free -m
