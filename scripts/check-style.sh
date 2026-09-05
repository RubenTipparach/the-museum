#!/usr/bin/env bash
# Enforce CLAUDE.md section 1: zero em dashes (U+2014) and zero en dashes (U+2013)
# anywhere in the repository. Matched by codepoint so this script stays clean ASCII
# and does not report itself. LC_ALL is required: \x{...} above 0x7F needs UTF-8.
#
# The matches are collected and tested for emptiness rather than read off grep's
# exit status: xargs may run grep more than once and reports 123 if any run found
# nothing, and grep reports 2 if any argument was unreadable even when it found a
# match. Either would have turned a found dash into a PASS. The itch project's
# links to data/ and assets/ are tracked as files and are directories here, so
# they are dropped from the list before grep sees them.
#
# Usage: ./scripts/check-style.sh
# Exit:  0 clean, 1 violations found.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

export LC_ALL=C.UTF-8
found="$(
  git ls-files -z \
    | grep -zvE '\.(jpg|jpeg|png|glb|gltf|blend|ptex|wav|ogg)$' \
    | while IFS= read -r -d '' f; do [[ -d "$f" ]] || printf '%s\0' "$f"; done \
    | xargs -0 grep -nP '\x{2014}|\x{2013}' -- || true
)"
if [[ -n "$found" ]]; then
  printf '%s\n' "$found"
  printf '\nFAIL: em dash (U+2014) or en dash (U+2013) found above.\n' >&2
  printf 'See CLAUDE.md section 1. Use a colon, a comma, a period, or a hyphen.\n' >&2
  exit 1
fi

printf 'PASS: no em dashes or en dashes found.\n'
