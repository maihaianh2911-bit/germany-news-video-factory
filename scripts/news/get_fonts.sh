#!/usr/bin/env bash
# Download the subtitle font of the videos (npm package @fontsource/philosopher, pinned) into <dir>/philosopher
# for scripts/news/fonts.py.
# Usage: scripts/news/get_fonts.sh <dir>
set -euo pipefail
mkdir -p "$1" && cd "$1"
if [ ! -f philosopher/index.css ]; then
  npm pack -q "@fontsource/philosopher@5.2.8" >/dev/null
  mkdir -p philosopher && tar -xzf fontsource-philosopher-5.2.8.tgz -C philosopher --strip-components=1
fi
ls "$1"
