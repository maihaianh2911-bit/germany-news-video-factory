#!/usr/bin/env bash
# Copy files into a folder of the 'renders' branch and push. Usage: scripts/publish_renders.sh <dest_dir|.> file1 [file2 ...]
set -euo pipefail
DEST="$1"; shift
URL="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
WT=$(mktemp -d)
if git fetch -q --depth 1 "$URL" renders:refs/remotes/origin/renders; then
  git worktree add -q "$WT" origin/renders
else   # new repo: the renders branch does not exist yet → start it empty
  git worktree add -q --detach "$WT"
  (cd "$WT" && git checkout -q --orphan renders && { git rm -rf -q . || true; } && git clean -fdq)
fi
mkdir -p "$WT/$DEST"; cp "$@" "$WT/$DEST/"
cd "$WT"; git config user.name render-bot; git config user.email render-bot@users.noreply.github.com
git add -A; git commit -q -m "publish $DEST ($GITHUB_RUN_ID)" || true
for i in 1 2 3; do
  git push -q "$URL" HEAD:renders && { echo "published to renders/$DEST"; exit 0; }
  git fetch -q --depth 1 "$URL" renders && git rebase -q FETCH_HEAD || true; sleep $((i * 5))
done
echo "::error::không đẩy được lên renders"; exit 1
