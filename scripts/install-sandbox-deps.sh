#!/usr/bin/env bash
# Install what the Claude Code sandbox (Ubuntu 24.04, no GPU, no display) needs
# to run the engine WITH its real renderer: a software Vulkan driver so Forward+
# can draw, Xvfb for a display, and the .NET SDK for the mono build.
#
# Idempotent. Needs root, which the sandbox has. On a developer machine with a
# GPU and a desktop none of this is needed.
#
# Usage: ./scripts/install-sandbox-deps.sh

set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../build.config"

need=()
dpkg -s mesa-vulkan-drivers >/dev/null 2>&1 || need+=(mesa-vulkan-drivers)
dpkg -s vulkan-tools        >/dev/null 2>&1 || need+=(vulkan-tools)
dpkg -s xvfb                >/dev/null 2>&1 || need+=(xvfb)
if [[ "$GODOT_FLAVOR" == "mono" ]]; then
  dpkg -s "dotnet-sdk-${DOTNET_MAJOR}.0" >/dev/null 2>&1 || need+=("dotnet-sdk-${DOTNET_MAJOR}.0")
fi

if (( ${#need[@]} )); then
  echo "installing: ${need[*]}"
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "${need[@]}" >/dev/null
fi

vulkaninfo --summary 2>/dev/null | grep -E 'deviceName|apiVersion' | head -2
[[ "$GODOT_FLAVOR" == "mono" ]] && dotnet --list-sdks
echo "sandbox deps ready"
