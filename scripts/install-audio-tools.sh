#!/usr/bin/env bash
# Install what the audio pipeline renders with: fluidsynth, the General MIDI
# soundfont it plays, and oggenc to encode the score (docs/AUDIO.md).
# Idempotent, so it is cheap to call from every render.
#
# Usage: ./scripts/install-audio-tools.sh

set -euo pipefail
SOUNDFONT="/usr/share/sounds/sf2/FluidR3_GM.sf2"

if command -v fluidsynth >/dev/null && [[ -f "$SOUNDFONT" ]] && command -v oggenc >/dev/null; then
  echo "audio tools present: $(fluidsynth --version 2>&1 | head -1)" >&2
  exit 0
fi

echo "installing fluidsynth, the GM soundfont and vorbis-tools" >&2
export DEBIAN_FRONTEND=noninteractive
if [[ "$(id -u)" == "0" ]]; then
  apt-get install -y -qq fluidsynth fluid-soundfont-gm vorbis-tools >&2
else
  sudo apt-get install -y -qq fluidsynth fluid-soundfont-gm vorbis-tools >&2
fi
[[ -f "$SOUNDFONT" ]] || { echo "the soundfont is still missing at $SOUNDFONT" >&2; exit 1; }
fluidsynth --version 2>&1 | head -1 >&2
