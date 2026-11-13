# germany-news-video-factory — notes for Claude

Read `docs/HANDOVER.md` first (the owner, their standing decisions, the current state), then `AGENT_NEWS.md` (how a
video is made). The owner is Vietnamese and not technical: answer in short, simple Vietnamese, no jargon.

This repo makes one thing: vertical German news shorts from real pictures, a German voice and subtitles timed to
it. The owner writes the scripts and sends them in a chat; everything after that is Claude's and the machine's.
One issue `[Tin tức] …` = one video; the machine steps run on GitHub Actions (`news.yml`), Claude's steps are in
`AGENT_NEWS.md`.

## When the owner pastes a script in a chat
1. Create one issue in `maihaianh2911-bit/germany-news-video-factory`: title `[Tin tức] <German headline> —
   <main idea in Vietnamese>`, body with these sections (same names as the issue form):
   `### Chủ đề (không bắt buộc)` / `### Kịch bản (bắt buộc)` = the script exactly as pasted /
   `### Giọng đọc (không bắt buộc)` = `_No response_` unless the owner names a voice /
   `### Ghi chú (không bắt buộc)` = wishes from the chat. No labels: the workflow adds them.
2. Do Claude's steps of `AGENT_NEWS.md` for that issue right away (claim with `news-busy` as written there):
   `script.json` → wait for the voice and pictures (~20–30 min for 40–60 lines) → `picks.json`, with the framing
   preview → wait for the render (~20–25 min) → check the shot sheet → closing comment. Use the GitHub tools of the
   session. While a machine step runs, say so in one line and wait; if the owner does not want to wait, stop after
   any step: the Claude task "japan-video-factory" (shared with the Japanese repo, see HANDOVER) continues from the
   labels when GitHub calls it (no hourly run; needs the two secrets).
3. Give the owner the links to the video, the subtitles and the picture credits.

The script is the owner's: translate and split it, never edit its content. Look at the pictures yourself,
preview before rendering.

## Changing the pipeline
Before pushing to `main`: `python3 tests/news_units.py`, `python3 tests/news_smoke.py --still`,
`python3 -m compileall -q scripts tests`, `npm run check`. Never touch secrets. Comments posted on GitHub start with 🤖 (they come from the owner's account).
No pull requests unless asked.
