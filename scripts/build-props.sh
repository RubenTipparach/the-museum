#!/usr/bin/env bash
# Build the exhibit's props, headless: assets/props/*.glb, the .blend beside
# them, and the proof render in docs/reference/.
#
# Usage: ./scripts/build-props.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLENDER="$(./scripts/install-blender.sh 2>/dev/null || "$ROOT/scripts/install-blender.sh")"
cd "$ROOT"
"$BLENDER" -b --python tools/build_props.py 2>&1 | grep -vE "^$|Color management|Blender quit"
