#!/usr/bin/env bash
# Install the pinned Godot editor into TOOLS_DIR. Version, release and flavor
# come from build.config so CI, the sandbox and a developer's machine install
# the identical toolchain. Idempotent.
#
# Downloaded from Godot's own endpoint, which is what godotengine.org/download
# links to; it redirects to Godot's object storage and it is reachable through
# the sandbox proxy, which github.com release downloads have not always been.
#
# Usage: ./scripts/install-godot.sh
#   Prints the path of the editor binary on its last line.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/build.config"

dest="$ROOT/$TOOLS_DIR/godot"
bin="$dest/godot"

if [[ -x "$bin" ]] && "$bin" --headless --version 2>/dev/null | grep -q "^$GODOT_VERSION"; then
  echo "$bin"; exit 0
fi

if [[ "$GODOT_FLAVOR" == "mono" ]]; then slug="mono_linux_x86_64.zip"; else slug="linux.x86_64.zip"; fi
url="https://downloads.godotengine.org/?version=$GODOT_VERSION&flavor=$GODOT_RELEASE&slug=$slug&platform=linux.64"

rm -rf "$dest"; mkdir -p "$dest"
echo "downloading $url" >&2
curl -sSL --fail --retry 3 --retry-delay 2 -o "$dest/godot.zip" "$url"
unzip -q -o "$dest/godot.zip" -d "$dest"
rm -f "$dest/godot.zip"

# The mono archive unpacks into a directory beside its GodotSharp runtime; the
# standard one is a bare binary. Normalise both to $bin without separating the
# executable from the files beside it.
found="$(find "$dest" -type f -name 'Godot_v*' -print -quit)"
[[ -n "$found" ]] || { echo "no Godot executable under $dest" >&2; exit 1; }
if [[ "$(dirname "$found")" != "$dest" ]]; then
  mv "$(dirname "$found")"/* "$dest"/; rmdir "$(dirname "$found")" 2>/dev/null || true
fi
mv "$dest/$(basename "$found")" "$bin"
chmod +x "$bin"
"$bin" --headless --version >&2
echo "$bin"
