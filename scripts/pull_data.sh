#!/usr/bin/env bash
set -euo pipefail

# Consumer-side helper (run on your other VPS)
# Usage:
#   MOOSE_DATA_URL=https://moose-core.tailnet/latest.json \
#   MOOSE_TOKEN=... \
#   ./pull_data.sh

: "${MOOSE_DATA_URL:?set MOOSE_DATA_URL}"
: "${MOOSE_TOKEN:?set MOOSE_TOKEN}"

OUT_DIR="${OUT_DIR:-./data}"
mkdir -p "$OUT_DIR"

curl -fsSL \
  -H "Authorization: Bearer ${MOOSE_TOKEN}" \
  "$MOOSE_DATA_URL" \
  -o "$OUT_DIR/latest.json"

echo "Pulled to $OUT_DIR/latest.json"
