#!/usr/bin/env bash
# Install butler, the itch.io upload tool, into TOOLS_DIR. Idempotent.
# Usage: ./scripts/install-butler.sh

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

readonly BUTLER_URL="https://broth.itch.zone/butler/linux-amd64/LATEST/archive/default"

main() {
  require_cmd curl
  require_cmd unzip
  if [[ -x "$BUTLER_BIN" ]]; then
    step "butler already installed"
    LD_LIBRARY_PATH="$(dirname "$BUTLER_BIN")" "$BUTLER_BIN" -V >&2 || true
    return 0
  fi
  step "Installing butler"
  local dest archive
  dest="$(dirname "$BUTLER_BIN")"
  mkdir -p "$dest"
  archive="$dest/butler.zip"
  log "downloading $BUTLER_URL"
  curl -sSL --fail --retry 3 --retry-delay 2 -o "$archive" "$BUTLER_URL" || die "butler download failed from $BUTLER_URL"
  unzip -q -o "$archive" -d "$dest" || die "butler archive did not unpack"
  rm -f "$archive"
  chmod +x "$BUTLER_BIN"
  [[ -x "$BUTLER_BIN" ]] || die "butler binary missing after unpack: $BUTLER_BIN"
  # The archive ships butler plus the libraries it needs for self updating.
  LD_LIBRARY_PATH="$dest" "$BUTLER_BIN" -V >&2 || die "butler installed but will not run"
}

main "$@"
