#!/usr/bin/env bash
# Copy files into a folder of the 'renders' branch and push. Usage: scripts/publish_renders.sh <dest_dir|.> file1 [file2 ...]
# Every attempt starts again from the freshly fetched tip of renders: rebasing shallow history can conflict and then
# push a commit without these files.
set -euo pipefail
DEST="$1"; shift
URL="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
WT=$(mktemp -d)
for i in 1 2 3 4; do
  rm -rf "$WT"; git worktree prune
  rc=0; git ls-remote --exit-code "$URL" refs/heads/renders > /dev/null || rc=$?
  if [ "$rc" = 2 ]; then   # new repo: the renders branch does not exist yet → start it empty
    git worktree add -q --detach "$WT"
    (cd "$WT" && git checkout -q --orphan "renders-new-$$-$i" && { git rm -rf -q . || true; } && git clean -fdq)
  elif [ "$rc" = 0 ] && git fetch -q --depth 1 "$URL" +refs/heads/renders:refs/remotes/origin/renders; then
    git worktree add -q --detach "$WT" origin/renders
  else
    echo "renders: không lấy được nhánh (lần $i)"; sleep $((i * 5)); continue
  fi
  mkdir -p "$WT/$DEST"; cp "$@" "$WT/$DEST/"
  if (cd "$WT" && git add -A \
      && { git -c user.name=render-bot -c user.email=render-bot@users.noreply.github.com commit -q -m "publish $DEST ($GITHUB_RUN_ID)" || true; } \
      && git push -q "$URL" HEAD:refs/heads/renders); then
    echo "published to renders/$DEST"; exit 0
  fi
  echo "renders: lần đẩy $i bị từ chối, làm lại từ bản mới nhất"; sleep $((i * 5))
done
echo "::error::không đẩy được lên renders sau 4 lần thử"; exit 1
