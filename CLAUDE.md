# germany-news-video-factory — notes for Claude

## Iron rules (owner, 16/11/2026; language changed by the owner on 20/11/2026) — they come before everything else in this file
1. **The video is in the channel's language: English (tiếng Anh).** Since 20/11/2026 this repo is the owner's
   American true-crime channel ("kênh vụ án Mỹ"), no longer the German news channel. The voice is the channel's
   English voice, and the script lines, subtitles and on-screen text are in English (tiếng Anh). A script that
   arrives in another language is translated faithfully into English (tiếng Anh) first. Never a voice or text of another language: check the language of `lines` and the voice before the voice
   step, and again on the finished video. A video in the wrong language is not delivered: fix it and render again.
2. **No video under 60 seconds.** Before the voice step, estimate the length from the script (use the seconds per
   line of this channel's earlier videos); after the voice step, read the real length of the speech (the machine
   comment gives it). If the video would be under 60 seconds, **write the script longer** (more true facts and
   detail on the same subject, in the owner's tone, nothing invented) until it passes 60 seconds, tell the owner on
   the issue what was added, and only then go on. This is the one exception to "never change the owner's script".
   Never render or deliver a video under 60 seconds. Only exception: a trial or sample video — the owner says so,
   or the issue title or notes say `thử`, `mẫu`, `test` or `demo`.

Read `docs/HANDOVER.md` first (the owner, their standing decisions, the current state), then `AGENT_NEWS.md` (how a
video is made). The owner is Vietnamese and not technical: answer in short, simple Vietnamese, no jargon.

This repo makes one thing: vertical English shorts about real American criminal cases, from real pictures, an
English voice and subtitles timed to it (the names `news`, `[Tin tức]`, `germany-news-video-factory` are left
from the German news channel it was until 20/11/2026; the video layout is unchanged — the owner re-edits the
pictures themselves). The owner writes the scripts and sends them in a chat; everything after that is Claude's and the machine's.
One issue `[Vụ án] …` (the old `[Tin tức] …` still works) = one video; the machine steps run on GitHub Actions (`news.yml`), Claude's steps are in
`AGENT_NEWS.md`.

## When you were started by GitHub (a Claude task, nobody in the chat)
The prompt may be as short as "Làm việc đang chờ trong repo này" ("do the work waiting in this repo"), and GitHub
adds a line such as "Phiếu vụ án Mỹ số 3: giọng và ảnh đã sẵn sàng". Then: follow `AGENT_NIGHTLY.md` of this repo (its first check lists the `news-*` issues waiting for you), then `AGENT_NEWS.md`. Nobody answers questions, so do not ask; comments go on the issues
(🤖, Vietnamese).

## When the owner pastes a script in a chat
1. Create one issue in `maihaianh2911-bit/germany-news-video-factory`: title `[Vụ án] <English headline> —
   <main idea in Vietnamese>`, body with these sections (same names as the issue form):
   `### Chủ đề (không bắt buộc)` / `### Kịch bản (bắt buộc)` = the script exactly as pasted /
   `### Giọng đọc (không bắt buộc)` = `_No response_` unless the owner names a voice /
   `### Ghi chú (không bắt buộc)` = wishes from the chat. No labels: the workflow adds them (`news`, `news-plan`).
2. **Right after creating the issue, add `news-busy`** (before anything else): opening the issue also wakes the
   Claude task, and the label tells it the issue is taken, so the two do not write `script.json` at the same time.
   Then do Claude's steps of `AGENT_NEWS.md` for that issue right away (keep `news-busy` while you work on a step,
   as written there): `script.json` → wait for the voice and pictures (~10–25 min: ~12 min for 22 lines, ~22 min
   for 46 lines) → `picks.json`, with the framing preview → wait for the render (~5–20 min: ~6.5 min for a
   1.5-minute video, ~19 min for 3 minutes) → check the shot sheet → closing comment. Use the GitHub tools of the
   session. While a machine step runs, say so in one line and wait; if the owner does not want to wait, stop after
   any step: the Claude task "japan-video-factory" (shared with the Japanese repo, see HANDOVER, or this repo's own
   task when each repo has its own seat) continues from the labels when GitHub calls it (no hourly run; needs the two secrets).
   Remove `news-busy` whenever you stop: while it is fresh (< 2 hours) the machine does not call the task for that
   issue. A machine comment ending with `⚠️ Chưa gọi được Claude …` means nobody was called: go on in the chat, or
   the owner presses "Gọi Claude ngay".
3. Give the owner the links to the video, the subtitles, the posting caption (`caption.txt`, written at the picks step, `AGENT_NEWS.md` §2.7) and the picture credits.

The script is the owner's: translate and split it, never edit its content (only exception: iron rule 2, a script too short for 60 seconds). Look at the pictures yourself,
preview before rendering.

## Changing the pipeline
Before pushing to `main`: `python3 tests/news_units.py`, `python3 tests/news_smoke.py --still`,
`python3 -m compileall -q scripts tests`, `npm run check`. They need
`pip install numpy scipy pillow num2words==0.5.14` (when `num2words` cannot build its `docopt` dependency:
`pip install docopt-ng && pip install --no-deps num2words==0.5.14`), `ffmpeg` (or `pip install imageio-ffmpeg==0.8.1`)
and `npm ci`; the first `--still` downloads Chrome Headless Shell (~110 MB). `check.yml` runs the same on GitHub,
plus `news_smoke.py --chapters`. Never touch secrets. Comments posted on GitHub start with 🤖 (they come from the owner's account).
No pull requests unless asked.
