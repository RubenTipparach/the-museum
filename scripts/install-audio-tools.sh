#!/usr/bin/env bash
# Install what the audio pipelines render with (docs/AUDIO.md):
#   csound      the effects, which are objects rather than instruments
#   fluidsynth  the score, plus the General MIDI soundfont it plays
#   sox         the mastering both come through, and oggenc the encode
# Idempotent, so it is cheap to call from every render.
#
# Usage: ./scripts/install-audio-tools.sh

set -euo pipefail
SOUNDFONT="/usr/share/sounds/sf2/FluidR3_GM.sf2"

if command -v csound >/dev/null && command -v fluidsynth >/dev/null \
   && command -v sox >/dev/null && command -v oggenc >/dev/null && [[ -f "$SOUNDFONT" ]]; then
  echo "audio tools present: $(csound --version 2>&1 | head -1), $(sox --version)" >&2
  exit 0
fi

echo "installing csound, fluidsynth, the GM soundfont, sox and vorbis-tools" >&2
export DEBIAN_FRONTEND=noninteractive
if [[ "$(id -u)" == "0" ]]; then
  apt-get install -y -qq csound fluidsynth fluid-soundfont-gm sox libsox-fmt-all vorbis-tools >&2
else
  sudo apt-get install -y -qq csound fluidsynth fluid-soundfont-gm sox libsox-fmt-all vorbis-tools >&2
fi
[[ -f "$SOUNDFONT" ]] || { echo "the soundfont is still missing at $SOUNDFONT" >&2; exit 1; }
csound --version 2>&1 | head -1 >&2
fluidsynth --version 2>&1 | head -1 >&2
sox --version >&2
