#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf build dist
uv run pyinstaller otklik-backend.spec --noconfirm --clean
echo "sidecar: $(pwd)/dist/backend/otklik-backend"
