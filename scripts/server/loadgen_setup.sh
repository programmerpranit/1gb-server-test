#!/usr/bin/env bash
# Provision the load-generator droplet. Runs ON THE LOAD GENERATOR as root. Idempotent, ~1 min.
# The load generator is stateless: run_test.sh copies the k6 script for every run and pulls results back.
#
# Usage: loadgen_setup.sh <k6_version>
set -euo pipefail
K6_VERSION="${1:?k6_version e.g. 2.3.0}"
export DEBIAN_FRONTEND=noninteractive

echo ">> base packages"
apt-get update -y
apt-get install -y ca-certificates curl python3

echo ">> k6 v$K6_VERSION (same version as the Mac, pinned)"
if ! command -v k6 >/dev/null || ! k6 version | grep -q "v$K6_VERSION"; then
  tmp="$(mktemp -d)"
  curl -fsSL "https://github.com/grafana/k6/releases/download/v${K6_VERSION}/k6-v${K6_VERSION}-linux-amd64.tar.gz" \
    | tar -xz -C "$tmp"
  install -m 0755 "$tmp/k6-v${K6_VERSION}-linux-amd64/k6" /usr/local/bin/k6
  rm -rf "$tmp"
fi

echo ">> limits + network tuning (k6 holds ~1 socket per VU)"
cat > /etc/security/limits.d/loadgen.conf <<EOF
*    soft nofile 1048576
*    hard nofile 1048576
root soft nofile 1048576
root hard nofile 1048576
EOF
cat > /etc/sysctl.d/90-loadgen.conf <<EOF
fs.file-max = 2097152
net.ipv4.ip_local_port_range = 10240 65535
net.ipv4.tcp_tw_reuse = 1
net.core.somaxconn = 4096
EOF
sysctl --system >/dev/null

mkdir -p /opt/loadgen/runs
timedatectl set-timezone UTC

echo ">> versions"
k6 version
. /etc/os-release && echo "$PRETTY_NAME"
nproc
free -m | awk '/Mem/{print "mem_total_mb=" $2}'
