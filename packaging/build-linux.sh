#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-0.0.0-dev}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

python3 -m pip install --upgrade pyinstaller
python3 -m PyInstaller --noconfirm --clean packaging/FlowWorklist.spec

dist/FlowWorklist/FlowWorklist --role diagnostics
cp packaging/linux/install-service.sh dist/FlowWorklist/install-service.sh
cp packaging/linux/flowworklist.service dist/FlowWorklist/flowworklist.service
touch dist/FlowWorklist/portable.mode
chmod +x dist/FlowWorklist/FlowWorklist dist/FlowWorklist/install-service.sh
tar -C dist -czf "dist/FlowWorklist-Portable-${VERSION}-Linux-x64.tar.gz" FlowWorklist
