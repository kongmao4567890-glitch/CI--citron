#!/bin/bash
# Compatibility wrapper.
#
# The Chinese patch is applied by tools/patch_citron.py, which anchors every edit on exact
# upstream source and fails loudly when an anchor is gone — a sed script silently no-ops instead,
# producing an English build that still passes CI. This wrapper keeps the old entry point working.
#
# Usage: ./patch-translation.sh [path/to/citron]   (default: ./citron)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "${SCRIPT_DIR}/tools/patch_citron.py" "${1:-./citron}"
