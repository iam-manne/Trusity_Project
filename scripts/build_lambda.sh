#!/usr/bin/env bash
set -euo pipefail
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../lambda_bulk_import" && pwd)"
rm -rf "${source_dir}/build"
mkdir -p "${source_dir}/build"
python -m pip install -r "${source_dir}/requirements.txt" -t "${source_dir}/build"
cp "${source_dir}/handler.py" "${source_dir}/build/handler.py"
(cd "${source_dir}/build" && zip -qr "../bulk-import.zip" .)
echo "Created ${source_dir}/bulk-import.zip"

