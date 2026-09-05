#!/usr/bin/env bash
# Validate that build.config and the itch project's export_presets.cfg agree:
# every name in ENABLED_TARGETS and DEPLOY_TARGETS has a row in TARGETS, every
# row's preset exists, and nothing is deployed that is never built.
# Usage: ./scripts/check-config.sh

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

failures=0
fail() { printf 'FAIL: %s\n' "$*" >&2; failures=$((failures + 1)); }
pass() { printf 'ok    %s\n' "$*"; }

step "Checking ENABLED_TARGETS and DEPLOY_TARGETS against the TARGETS table"
for list in ENABLED_TARGETS DEPLOY_TARGETS; do
  for name in ${!list}; do
    if resolve_target "$name" >/dev/null 2>&1; then pass "$list target '$name' is defined"
    else fail "$list names '$name', which has no row in TARGETS"; fi
  done
done

step "Checking every deployed target is also built"
for name in $DEPLOY_TARGETS; do
  found=0
  for built in $ENABLED_TARGETS; do [[ "$built" == "$name" ]] && found=1 && break; done
  if [[ "$found" == 1 ]]; then pass "deploy target '$name' is in ENABLED_TARGETS"
  else fail "DEPLOY_TARGETS names '$name', which ENABLED_TARGETS does not build"; fi
done

step "Checking Godot presets against $GODOT_PROJECT_DIR/export_presets.cfg"
presets_file="$PROJECT_PATH/export_presets.cfg"
if [[ ! -f "$presets_file" ]]; then
  fail "export_presets.cfg not found in $PROJECT_PATH"
else
  mapfile -t declared < <(grep -oP '(?<=^name=")[^"]+' "$presets_file" 2>/dev/null || true)
  printf '  presets: %s\n' "${declared[*]:-none}" >&2
  while read -r name; do
    [[ -z "$name" ]] && continue
    load_target "$name"
    found=0
    for d in "${declared[@]:-}"; do [[ "$d" == "$TARGET_PRESET" ]] && found=1 && break; done
    if [[ "$found" == 1 ]]; then pass "target '$name' -> preset '$TARGET_PRESET'"
    else fail "target '$name' wants preset '$TARGET_PRESET', not in export_presets.cfg"; fi
  done < <(known_targets)
fi

step "Checking the generated scene and the assets match their sources"
if python3 "$REPO_ROOT/tools/gen_itch_scene.py" --check; then pass "exhibit.tscn matches the layout"; else fail "exhibit.tscn has drifted from the layout; rerun tools/gen_itch_scene.py"; fi
if python3 "$REPO_ROOT/tools/gen_sfx.py" --check >/dev/null; then pass "the sound effects match their generator"; else fail "a sound effect drifts from tools/gen_sfx.py"; fi

if [[ "$failures" -gt 0 ]]; then
  printf '\n%d problem(s) found.\n' "$failures" >&2
  exit 1
fi
printf '\nConfig is consistent.\n'
