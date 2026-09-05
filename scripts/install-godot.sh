#!/usr/bin/env bash
# Install a pinned Godot editor into TOOLS_DIR. Version and release come from
# build.config so CI, the sandbox and a developer's machine install the same
# toolchain. Idempotent. Prints the path of the editor binary on its last line.
#
# Usage: ./scripts/install-godot.sh [mono|standard]
#   mono      (default) the C# editor for the desktop track and ADR-0's render
#             proof, into .tools/godot
#   standard  the GDScript editor for the itch track, into .tools/godot-standard,
#             with the Web export templates it needs
#
# Downloaded from Godot's own endpoint, which is what godotengine.org/download
# links to; it is reachable through the sandbox proxy, which github.com release
# downloads have not always been.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/build.config"

flavor="${1:-$GODOT_FLAVOR}"
case "$flavor" in
  mono) dest="$ROOT/$TOOLS_DIR/godot"; slug="mono_linux_x86_64.zip" ;;
  standard) dest="$ROOT/$TOOLS_DIR/godot-standard"; slug="linux.x86_64.zip" ;;
  *) echo "flavor must be mono or standard, got '$flavor'" >&2; exit 1 ;;
esac
bin="$dest/godot"
base="https://downloads.godotengine.org/?version=$GODOT_VERSION&flavor=$GODOT_RELEASE&platform=linux.64"

if ! { [[ -x "$bin" ]] && "$bin" --headless --version 2>/dev/null | grep -q "^$GODOT_VERSION"; }; then
  rm -rf "$dest"; mkdir -p "$dest"
  echo "downloading $base&slug=$slug" >&2
  curl -sSL --fail --retry 3 --retry-delay 2 -o "$dest/godot.zip" "$base&slug=$slug"
  unzip -q -o "$dest/godot.zip" -d "$dest"
  rm -f "$dest/godot.zip"
  # The mono archive unpacks into a directory beside its GodotSharp runtime;
  # the standard one is a bare binary. Normalise both to $bin without
  # separating the executable from the files beside it.
  found="$(find "$dest" -type f -name 'Godot_v*' -print -quit)"
  [[ -n "$found" ]] || { echo "no Godot executable under $dest" >&2; exit 1; }
  if [[ "$(dirname "$found")" != "$dest" ]]; then
    mv "$(dirname "$found")"/* "$dest"/; rmdir "$(dirname "$found")" 2>/dev/null || true
  fi
  mv "$dest/$(basename "$found")" "$bin"
  chmod +x "$bin"
fi

# The Web export templates, for the standard flavor only: Godot looks for
# them under its own data directory, named for the version. Only the web
# ones are unpacked; the archive is 1.3 GB and the rest of it is other
# platforms.
if [[ "$flavor" == "standard" ]]; then
  tdir="$HOME/.local/share/godot/export_templates/$GODOT_VERSION.$GODOT_RELEASE"
  if [[ ! -f "$tdir/web_nothreads_release.zip" ]]; then
    mkdir -p "$tdir"
    echo "downloading the export templates" >&2
    curl -sSL --fail --retry 3 --retry-delay 2 -o "$dest/templates.tpz" "$base&slug=export_templates.tpz"
    unzip -q -o -j "$dest/templates.tpz" 'templates/web_*' 'templates/version.txt' -d "$tdir"
    rm -f "$dest/templates.tpz"
  fi
fi

"$bin" --headless --version >&2
echo "$bin"
