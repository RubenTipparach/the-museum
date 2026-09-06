#!/usr/bin/env bash
# Prove the exported web build actually boots: serve builds/web, open it in
# headless Chromium and require the game to print its smoke marker from the
# end of main.gd's _ready, then write a frame of it to docs/reference.
#
# An export that succeeds is not a build that works: a missing file, a script
# error at runtime or a texture format the browser cannot take all survive
# the export and die in the page. itch/tests/web_boot.mjs is the check.
#
# Usage: ./scripts/verify-build.sh
# Exit:  0 the build boots, 1 it does not.

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

main() {
  load_target "web"
  [[ -s "$TARGET_OUTPUT" ]] || die "no web build at $TARGET_OUTPUT. Run scripts/build.sh web first."
  require_cmd node
  step "Booting $TARGET_OUTPUT in headless Chromium"
  node "$PROJECT_PATH/tests/web_boot.mjs" "$(dirname "$TARGET_OUTPUT")" || die "the web build did not boot"
  step "Build boots and runs its scripts"
}

main "$@"
