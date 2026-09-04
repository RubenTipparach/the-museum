#!/usr/bin/env bash
# Build one exhibit's shell from its layout file, headless: the .blend and the
# .glb in assets/exhibit/, and the proof render in docs/reference/.
#
# Usage: ./scripts/build-exhibit.sh [elmorian]

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLENDER="$(./scripts/install-blender.sh 2>/dev/null || "$ROOT/scripts/install-blender.sh")"
cd "$ROOT"
"$BLENDER" -b --python tools/build_exhibit.py -- "${1:-elmorian}" 2>&1 | grep -vE "^$|Color management|Blender quit"
