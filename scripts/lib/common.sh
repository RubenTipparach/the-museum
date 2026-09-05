#!/usr/bin/env bash
#
# shellcheck disable=SC2034
# SC2034 is disabled for this file only: it reports "appears unused" for the
# variables this library exists to define. ShellCheck reads one file at a time
# and cannot see the scripts that source this one.
#
# Shared helpers for every script in scripts/ that touches the itch track:
# config loading, target resolution, version stamping and the two Godot
# workarounds, once (CLAUDE.md 4.1). Adopted from RubenTipparach/the-federation
# scripts/lib/common.sh, where each of these earned its comment.
#
# Not executable on its own. Source it:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
readonly REPO_ROOT

# --- Logging -----------------------------------------------------------------

log()  { printf '  %s\n'      "$*" >&2; }
step() { printf '\n==> %s\n'  "$*" >&2; }
warn() { printf 'WARN: %s\n'  "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# --- Config ------------------------------------------------------------------

load_config() {
  local config="$REPO_ROOT/build.config"
  [[ -f "$config" ]] || die "missing config: $config"
  # shellcheck source=/dev/null
  source "$config"

  local required=(
    GODOT_VERSION GODOT_RELEASE ITCH_GODOT_FLAVOR GODOT_PROJECT_DIR
    ITCH_USER ITCH_GAME
    ENABLED_TARGETS DEPLOY_TARGETS TARGETS
    BUILD_DIR TOOLS_DIR
  )
  local name
  for name in "${required[@]}"; do
    [[ -n "${!name:-}" ]] || die "build.config does not set $name"
  done

  BUILD_PATH="$REPO_ROOT/$BUILD_DIR"
  TOOLS_PATH="$REPO_ROOT/$TOOLS_DIR"
  PROJECT_PATH="$REPO_ROOT/$GODOT_PROJECT_DIR"

  # Godot names its export template directory after the version.
  GODOT_TEMPLATE_VERSION="$GODOT_VERSION.$GODOT_RELEASE"
  GODOT_TEMPLATES="$HOME/.local/share/godot/export_templates/$GODOT_TEMPLATE_VERSION"

  # The itch track is the standard (GDScript) editor; the desktop track's
  # mono editor lives beside it in .tools/godot. scripts/install-godot.sh
  # installs either from its flavor argument.
  GODOT_BIN="$TOOLS_PATH/godot-$ITCH_GODOT_FLAVOR/godot"
  BUTLER_BIN="$TOOLS_PATH/butler/butler"
}

# --- Targets -----------------------------------------------------------------

trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  printf '%s' "${s%"${s##*[![:space:]]}"}"
}

# Print the TARGETS row for a name, pipe delimited and trimmed. Returns 1
# without printing for an unknown target; callers that report several bad
# names at once need it not to die.
resolve_target() {
  local want="$1" name preset subdir filename channel
  while IFS='|' read -r name preset subdir filename channel; do
    name="$(trim "$name")"
    [[ -z "$name" || "$name" == \#* ]] && continue
    if [[ "$name" == "$want" ]]; then
      printf '%s|%s|%s|%s\n' "$(trim "$preset")" "$(trim "$subdir")" "$(trim "$filename")" "$(trim "$channel")"
      return 0
    fi
  done <<< "$TARGETS"
  return 1
}

known_targets() {
  local name rest
  while IFS='|' read -r name rest; do
    name="$(trim "$name")"
    [[ -z "$name" || "$name" == \#* ]] && continue
    printf '%s\n' "$name"
  done <<< "$TARGETS"
}

unknown_target_error() {
  printf "unknown target '%s'. Known targets: %s" "$1" "$(known_targets | tr '\n' ' ')"
}

# Sets TARGET_PRESET TARGET_SUBDIR TARGET_FILENAME TARGET_CHANNEL TARGET_OUTPUT.
load_target() {
  local name="$1" row
  row="$(resolve_target "$name")" || die "$(unknown_target_error "$name")"
  IFS='|' read -r TARGET_PRESET TARGET_SUBDIR TARGET_FILENAME TARGET_CHANNEL <<< "$row"
  TARGET_OUTPUT="$BUILD_PATH/$TARGET_SUBDIR/$TARGET_FILENAME"
}

# Populate SELECTED_TARGETS from the arguments, else from the fallback list.
# Command substitution rather than a process substitution, so a die() inside
# stops the caller instead of leaving it with an empty list.
read_selected_targets() {
  local raw
  raw="$(selected_targets "$@")" || exit 1
  mapfile -t SELECTED_TARGETS <<< "$raw"
}

selected_targets() {
  local fallback="$1"
  shift
  local requested=("$@") name
  [[ ${#requested[@]} -eq 0 ]] && read -r -a requested <<< "$fallback"
  [[ ${#requested[@]} -eq 0 ]] && die "no targets requested and the default target list is empty"
  for name in "${requested[@]}"; do
    resolve_target "$name" >/dev/null || die "$(unknown_target_error "$name")"
  done
  printf '%s\n' "${requested[@]}"
}

# --- Version -----------------------------------------------------------------

# Stamped onto itch.io builds with butler --userversion: a tag when there is
# one, else a commit count and short sha so untagged builds still sort.
build_version() {
  if [[ -n "${BUILD_VERSION:-}" ]]; then
    printf '%s\n' "$BUILD_VERSION"
    return
  fi
  if ! git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
    printf '0.0.0-unknown\n'
    return
  fi
  local described
  if described="$(git -C "$REPO_ROOT" describe --tags --dirty 2>/dev/null)"; then
    printf '%s\n' "${described#v}"
  else
    printf '0.0.0-r%s-%s\n' "$(git -C "$REPO_ROOT" rev-list --count HEAD)" "$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
  fi
}

# --- Guards ------------------------------------------------------------------

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "required command not found: $1"
}

require_env() {
  [[ -n "${!1:-}" ]] || die "required environment variable not set: $1"
}

require_godot() {
  [[ -x "$GODOT_BIN" ]] || die "Godot not installed at $GODOT_BIN. Run scripts/install-godot.sh $ITCH_GODOT_FLAVOR first."
}

require_godot_project() {
  [[ -f "$PROJECT_PATH/project.godot" ]] || die "no project.godot in $PROJECT_PATH"
  [[ -f "$PROJECT_PATH/export_presets.cfg" ]] || die "no export_presets.cfg in $PROJECT_PATH"
}

# Run Godot, tolerating the nonzero status it returns for benign warnings,
# but never a crash: a status of 128+N means it died on signal N.
run_godot() {
  local status=0
  "$GODOT_BIN" "$@" >&2 || status=$?
  if (( status >= 128 )); then
    die "Godot crashed with exit $status (signal $((status - 128))) running:
       $GODOT_BIN $*"
  fi
  return 0
}

# Godot must generate .godot/ before an export or a script run behaves. On a
# clean checkout 4.7.1 aborts if --import runs cold, so the cold pass is
# primed with --editor --quit first. Shared by build.sh and run-tests.sh.
ensure_imported() {
  if [[ ! -d "$PROJECT_PATH/.godot" ]]; then
    log "cold project, priming the import with --editor --quit"
    "$GODOT_BIN" --headless --path "$PROJECT_PATH" --editor --quit >&2 || true
  fi
  run_godot --headless --path "$PROJECT_PATH" --import
  [[ -d "$PROJECT_PATH/.godot" ]] || die "import did not produce .godot/, cannot continue"
}
