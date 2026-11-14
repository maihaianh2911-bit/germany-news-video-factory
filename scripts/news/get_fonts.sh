#!/usr/bin/env bash
# Download the fonts of the news videos (npm packages @fontsource-variable/source-serif-4 and source-sans-3,
# pinned) into <dir>/source-serif-4 and <dir>/source-sans-3 for scripts/news/fonts.py.
# Usage: scripts/news/get_fonts.sh <dir>
set -euo pipefail
mkdir -p "$1" && cd "$1"
for p in source-serif-4 source-sans-3; do
  [ -f "$p/index.css" ] && continue
  npm pack -q "@fontsource-variable/$p@5.3.1" >/dev/null
  mkdir -p "$p" && tar -xzf "fontsource-variable-$p-5.3.1.tgz" -C "$p" --strip-components=1
done
ls "$1"
