#!/usr/bin/env bash
# The itch track's suites: the puzzles solved headless with no scene
# (CLAUDE.md 4.3), then the real main scene rendered room by room under xvfb
# on the software GL driver (CLAUDE.md 10), frames written to docs/reference.
#
# Usage: ./scripts/run-tests.sh
# Exit:  0 all checks pass, 1 otherwise.

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

main() {
  require_godot
  require_godot_project
  ensure_imported

  step "Running the puzzle tests"
  local out status=0
  out="$(mktemp)"
  "$GODOT_BIN" --headless --path "$PROJECT_PATH" --script res://tests/run_tests.gd >"$out" 2>&1 || status=$?
  sed 's/^/  /' "$out" >&2
  (( status >= 128 )) && { rm -f "$out"; die "test run crashed (exit $status)"; }
  grep -q "CHECKS PASSED" "$out" || { rm -f "$out"; die "puzzle tests failed"; }
  rm -f "$out"

  # The scene test needs a rendering context, so it runs under xvfb. A skip
  # has to be loud: CI installs xvfb precisely so this branch is never taken.
  if ! command -v xvfb-run >/dev/null; then
    [[ -n "${CI:-}" ]] && die "xvfb-run is missing in CI, so the scene test cannot run"
    step "Skipping the scene test locally (xvfb-run not installed)"
    return 0
  fi
  step "Rendering every room and station (390x844)"
  out="$(mktemp)"
  status=0
  xvfb-run -a "$GODOT_BIN" --path "$PROJECT_PATH" --rendering-driver opengl3 --resolution 390x844 \
    --script res://tests/scene_test.gd >"$out" 2>&1 || status=$?
  grep -E '^  ok|FAIL|SCRIPT ERROR|CHECKS PASSED' "$out" | sed 's/^/  /' >&2
  grep -q "SCENE CHECKS PASSED" "$out" || { sed 's/^/  | /' "$out" >&2; rm -f "$out"; die "scene test failed"; }
  rm -f "$out"
  step "Every room renders"
}

main "$@"
