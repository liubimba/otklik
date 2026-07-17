#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
OUT="../../apps/desktop/src-tauri/resources"

rm -rf build dist
uv run pyinstaller otklik-backend.spec --noconfirm --clean
mkdir -p "$OUT"
rm -rf "$OUT/backend"
cp -r dist/backend "$OUT/backend"
echo "sidecar: $OUT/backend/otklik-backend"
