#!/usr/bin/env bash
# Render every sound from its MIDI source and check what comes out
# (docs/AUDIO.md). The effects and the score are regenerated, never patched.
#
# Usage: ./scripts/render-audio.sh          # render, then gate
#        ./scripts/render-audio.sh --check  # gate only, and fail on drift

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
./scripts/install-audio-tools.sh >/dev/null

if [[ "${1:-}" == "--check" ]]; then
  python3 tools/gen_sfx.py --check
  python3 tools/gen_music.py --check
else
  python3 tools/gen_sfx.py
  python3 tools/gen_music.py
fi
python3 tools/check_audio.py
