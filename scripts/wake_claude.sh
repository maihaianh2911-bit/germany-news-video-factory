#!/usr/bin/env bash
# Start the Claude Code task right away (its API trigger). This is the only way Claude starts on its own: there is
# no hourly run. Needs repo secrets CLAUDE_TASK_URL (the task's "Fire URL") and CLAUDE_TASK_TOKEN. Never fails the
# workflow. The call is tried 3 times; with --issue N the issue gets one comment that says what happens next, or,
# when Claude could not be called, which button to press ("Gọi Claude ngay"); an issue with a fresh news-busy label
# is left to the Claude session that holds it. Details: scripts/news/wake.py.
# Usage: scripts/wake_claude.sh "<why>" [--issue N] [--say "<what the machine did>"] [--then "<what Claude does next>"] [--tail "<links>"]
python3 "$(dirname "$0")/news/wake.py" "$@" || true
exit 0
