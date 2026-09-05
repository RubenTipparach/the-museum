#!/usr/bin/env bash
# Export the itch track (the Godot project in GODOT_PROJECT_DIR) for one or
# more targets. The only place the project is exported: CI calls this rather
# than restating the export in workflow YAML (CLAUDE.md 4.1).
#
# Usage:
#   ./scripts/build.sh            # every target in ENABLED_TARGETS
#   ./scripts/build.sh web        # one target
# Environment:
#   EXPORT_MODE   "release" (default) or "debug"

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

readonly EXPORT_MODE="${EXPORT_MODE:-release}"

build_target() {
  local name="$1"
  load_target "$name"
  step "Exporting $name ($TARGET_PRESET, $EXPORT_MODE)"

  # Clean the target's output directory so a stale artifact can never be
  # mistaken for a fresh one. The path is proven to sit inside BUILD_PATH
  # first, because this is an rm -rf on a computed path.
  local out_dir
  out_dir="$(dirname "$TARGET_OUTPUT")"
  case "$out_dir" in
    "$BUILD_PATH"/*) ;;
    *) die "refusing to clean '$out_dir': not inside $BUILD_PATH" ;;
  esac
  mkdir -p "$out_dir"
  rm -rf -- "${out_dir:?}"/*

  local flag="--export-release"
  [[ "$EXPORT_MODE" == "debug" ]] && flag="--export-debug"

  # Godot returns nonzero for export warnings as well as failures, so success
  # is judged by whether the artifact exists and is non-empty.
  run_godot --headless --path "$PROJECT_PATH" "$flag" "$TARGET_PRESET" "$TARGET_OUTPUT"
  [[ -s "$TARGET_OUTPUT" ]] || die \
    "export produced no artifact at $TARGET_OUTPUT
       Preset '$TARGET_PRESET' must exist in $GODOT_PROJECT_DIR/export_presets.cfg and its
       export templates must be installed. Re-run scripts/install-godot.sh standard."
  log "$(du -h "$TARGET_OUTPUT" | cut -f1)  $TARGET_OUTPUT"
}

main() {
  read_selected_targets "$ENABLED_TARGETS" "$@"
  local targets=("${SELECTED_TARGETS[@]}")
  require_godot_project
  require_godot
  step "Building version $(build_version) for: ${targets[*]}"
  step "Importing project"
  ensure_imported
  local name
  for name in "${targets[@]}"; do
    build_target "$name"
  done
  step "Build complete"
  find "$BUILD_PATH" -type f -printf '  %s bytes  %p\n' >&2 2>/dev/null || true
}

main "$@"
