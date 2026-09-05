#!/usr/bin/env bash
# Install the pinned Blender into TOOLS_DIR and print its path. Idempotent.
# Blender needs a handful of X and GL libraries even headless; the sandbox
# has apt, so they are installed here rather than documented somewhere.
#
# Usage: ./scripts/install-blender.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/build.config"

dest="$ROOT/$TOOLS_DIR/blender"
bin="$dest/blender"
if [[ -x "$bin" ]] && "$bin" -b --version 2>/dev/null | grep -q "Blender $BLENDER_VERSION"; then echo "$bin"; exit 0; fi

if command -v apt-get >/dev/null && [[ "$(id -u)" == 0 ]]; then
  need=(); for p in libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libglu1-mesa libsm6 libxkbcommon0 libegl1; do dpkg -s "$p" >/dev/null 2>&1 || need+=("$p"); done
  if (( ${#need[@]} )); then apt-get update -qq; DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}" >/dev/null; fi
fi

major="${BLENDER_VERSION%.*}"
url="https://download.blender.org/release/Blender${major}/blender-${BLENDER_VERSION}-linux-x64.tar.xz"
rm -rf "$dest"; mkdir -p "$dest"
echo "downloading $url" >&2
curl -sSL --fail --retry 3 --retry-delay 2 -o "$dest/blender.tar.xz" "$url"
tar xJf "$dest/blender.tar.xz" -C "$dest" --strip-components=1
rm -f "$dest/blender.tar.xz"
"$bin" -b --version 2>/dev/null | head -1 >&2
echo "$bin"
