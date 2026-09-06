#!/usr/bin/env bash
# Push built artifacts to itch.io with butler.
#
# Usage:
#   ./scripts/deploy-itch.sh          # every target in DEPLOY_TARGETS
#   ./scripts/deploy-itch.sh web      # one target
# Environment:
#   BUTLER_API_KEY   required. An itch.io API key with upload rights; a CI
#                    secret, never in this repository.
#   DRY_RUN          1 to validate everything and print the commands only.
#
# Targets resolve through the same lib/common.sh code build.sh uses, so a
# channel can never drift from the artifact it carries.

source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"
load_config

readonly DRY_RUN="${DRY_RUN:-0}"

butler_run() {
  LD_LIBRARY_PATH="$(dirname "$BUTLER_BIN")" "$BUTLER_BIN" "$@"
}

push_target() {
  local name="$1" version="$2"
  load_target "$name"
  # The whole output directory, never the single artifact: a web export is
  # an html page, a wasm, a pck and a loader, and a push of the page alone is
  # a page that cannot start.
  local push_path
  push_path="$(dirname "$TARGET_OUTPUT")"
  [[ -s "$TARGET_OUTPUT" ]] || die "nothing to push for '$name': $TARGET_OUTPUT is missing. Run scripts/build.sh $name first."
  local slug="$ITCH_USER/$ITCH_GAME:$TARGET_CHANNEL"
  step "Pushing $name to $slug (version $version)"
  if [[ "$DRY_RUN" == "1" ]]; then
    log "DRY_RUN, would run:"
    log "butler push $push_path $slug --userversion $version"
    return 0
  fi
  butler_run push "$push_path" "$slug" --userversion "$version" || die "butler push failed for $name
       If this is the first upload, confirm https://$ITCH_USER.itch.io/$ITCH_GAME exists;
       butler cannot create a project page."
}

main() {
  read_selected_targets "$DEPLOY_TARGETS" "$@"
  local targets=("${SELECTED_TARGETS[@]}") version
  version="$(build_version)"
  [[ -x "$BUTLER_BIN" ]] || die "butler not installed at $BUTLER_BIN. Run scripts/install-butler.sh first."
  if [[ "$DRY_RUN" != "1" ]]; then
    require_env BUTLER_API_KEY
    export BUTLER_API_KEY
  fi
  step "Deploying version $version to $ITCH_USER/$ITCH_GAME: ${targets[*]}"
  local name
  for name in "${targets[@]}"; do
    push_target "$name" "$version"
  done
  if [[ "$DRY_RUN" == "1" ]]; then
    step "Dry run complete, nothing uploaded"
    return 0
  fi
  # Per channel, and not immediately. A push returns as soon as the bytes are
  # in ("Build is now processing"), and the channel does not exist until
  # itch.io has finished with them, so asking about the project a second later
  # printed "No channel found" over a push that had worked: a deploy that
  # looked failed and was not. Ask about the channel actually pushed, give it
  # a few seconds, and say plainly that processing is not an error.
  local name
  for name in "${targets[@]}"; do
    load_target "$name"
    step "Waiting for itch.io to process $TARGET_CHANNEL"
    local tries
    for tries in 1 2 3 4 5; do
      if butler_run status "$ITCH_USER/$ITCH_GAME:$TARGET_CHANNEL" 2>&1 | tee /dev/stderr | grep -q "^Channel"; then
        break
      fi
      [[ "$tries" == 5 ]] && log "still processing; itch.io finishes on its own, the upload is done"
      sleep 5
    done
  done
  step "Deploy complete: https://$ITCH_USER.itch.io/$ITCH_GAME"
}

main "$@"
