#!/usr/bin/env bash
# Render every .strudel pattern in assets/audio/music to an .ogg beside it,
# offline, with the vendored Strudel renderer (tools/strudel, ADR-12).
#
# Usage: ./scripts/render-music.sh            # every pattern
#        ./scripts/render-music.sh hall_six   # one
# Needs node and oggenc (apt package vorbis-tools). npm installs the renderer's
# packages on first run.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
command -v oggenc >/dev/null || { echo "oggenc missing: apt-get install vorbis-tools" >&2; exit 1; }
[[ -d tools/strudel/node_modules/@strudel ]] || (cd tools/strudel && npm install --no-audit --no-fund --loglevel=error)

for src in assets/audio/music/${1:-*}.strudel; do
  name="$(basename "$src" .strudel)"
  # the first line that sets the length: "// ... the render is N cycles"
  cycles="$(grep -oE 'render is [0-9]+ cycles' "$src" | grep -oE '[0-9]+' || echo 32)"
  wav="$(mktemp --suffix=.wav)"
  node tools/strudel/render_offline.mjs "$src" "$wav" "$cycles" 4
  oggenc -Q -q 4 -o "assets/audio/music/$name.ogg" "$wav"
  rm -f "$wav"
  ls -la "assets/audio/music/$name.ogg"
done
