#!/usr/bin/env bash
# Prove the engine RENDERS in this environment: import the lightproof project,
# compile its C# with dotnet, draw a Forward+ scene with twelve shadow casting
# lights and volumetric fog on the software Vulkan driver under Xvfb, and write
# the frame to docs/reference/forward_plus_lavapipe_proof.png.
#
# This is the check behind requirement 0 (docs/ARCHITECTURE.md ADR-0). Run it in
# a fresh session before trusting any visual claim, and run it after touching
# build.config. It fails loudly if the frame is black, because a renderer that
# starts and draws nothing is the failure the check exists to catch.
#
# Usage: ./scripts/render-proof.sh
# Exit:  0 a lit frame was written, 1 otherwise.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
source build.config

./scripts/install-sandbox-deps.sh >/dev/null
GODOT="$(./scripts/install-godot.sh)"
PROJ="$ROOT/tools/lightproof"
export DOTNET_CLI_TELEMETRY_OPTOUT=1

echo "importing" >&2
timeout 300 "$GODOT" --headless --path "$PROJ" --import >/dev/null 2>&1 || true
echo "building C#" >&2
dotnet build "$PROJ/lightproof.csproj" -c Debug --nologo -v q 2>&1 | tail -2 >&2

echo "rendering on software Vulkan" >&2
out="$(mktemp)"
timeout 600 xvfb-run -a "$GODOT" --path "$PROJ" \
  --rendering-driver vulkan --rendering-method forward_plus --quit-after 60 \
  >"$out" 2>&1 || true
grep -E '^(Vulkan|SHOT)' "$out" >&2 || { cat "$out" >&2; echo "FAIL: no frame" >&2; exit 1; }

shot="$HOME/.local/share/godot/app_userdata/lightproof/forward_plus_lights.png"
[[ -f "$shot" ]] || { echo "FAIL: screenshot not written" >&2; exit 1; }
cp "$shot" docs/reference/forward_plus_lavapipe_proof.png

# A black frame is a renderer that ran and drew nothing. Require some lit
# pixels. The check is pure stdlib on purpose: it has to run wherever the
# engine runs, and an import of Pillow here once turned a green render into a
# red job on a runner that had every other tool and not that one.
python3 tools/lit_fraction.py docs/reference/forward_plus_lavapipe_proof.png
echo "PASS: docs/reference/forward_plus_lavapipe_proof.png"
