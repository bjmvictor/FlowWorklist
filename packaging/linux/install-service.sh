#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root."
  exit 1
fi

install -d -m 0755 /opt/flowworklist
cp -a . /opt/flowworklist/
rm -f /opt/flowworklist/portable.mode
id flowworklist >/dev/null 2>&1 || useradd --system --home /var/lib/flowworklist --shell /usr/sbin/nologin flowworklist
install -d -o flowworklist -g flowworklist -m 0750 /var/lib/flowworklist
install -m 0644 /opt/flowworklist/flowworklist.service /etc/systemd/system/flowworklist.service
systemctl daemon-reload
systemctl enable --now flowworklist.service
echo "FlowWorklist is available at http://127.0.0.1:5000"
