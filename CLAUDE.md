# germany-news-video-factory — notes for Claude

## Iron rules (owner, 16/11/2026) — they come before everything else in this file
1. **The video is in the channel's language: German (tiếng Đức).** The voice is the channel's German voice, and the script lines, subtitles and
   on-screen text are in German (tiếng Đức). A script that arrives in another language is translated faithfully into German (tiếng Đức)
   first. Never a voice or text of another language: check the language of `lines` and the voice before the voice
   step, and again on the finished video. A video in the wrong language is not delivered: fix it and render again.
2. **No video under 60 seconds.** Before the voice step, estimate the length from the script (use the seconds per
   line of this channel's earlier videos); after the voice step, read the real length of the speech (the machine
   comment gives it). If the video would be under 60 seconds, **write the script longer** (more true facts and
   detail on the same subject, in the owner's tone, nothing invented) until it passes 60 seconds, tell the owner on
   the issue what was added, and only then go on. This is the one exception to "never change the owner's script".
   Never render or deliver a video under 60 seconds. Only exception: a trial or sample video — the owner says so,
   or the issue title or notes say `thử`, `mẫu`, `test` or `demo`.

Read `docs/HANDOVER.md` first (the owner, their standing decisions, the current state), then `AGENT_NEWS.md` (how a
video is made). The owner is Vietnamese and not technical: answer in short, simple Vietnamese, no jargon. They write
"tao" (I) and "mày" (you); answer the same way, "tao" for yourself and "mày" for them (as recorded in their Japanese
repo `maihaianh2911-bit/japan-news-video-factory`, whose way of working the owner asked to learn on 18/11/2026).
Show a script as one continuous text (the German in one piece, then its Vietnamese meaning in one piece), never in
numbered lines or bullet points (owner, 18/11: "Kịch bản phải liền mạch … đừng bao giờ chia đoạn ra như thế").

This repo makes one thing: vertical **German literature** shorts in German (the life of a writer, a work) from
real pictures, a German voice and yellow subtitles timed to it, written and edited like the owner's sample
(`00-video-mau/van-hoc-tolstoy.md`; owner's decision 14/11/2026, it replaced the news channel). The owner names a
writer or a work (or sends a script) in a chat; everything after that is Claude's and the machine's. One issue
`[Văn học] …` = one video; the machine steps run on GitHub Actions (`news.yml`; the machine still says "news"),
Claude's steps are in `AGENT_NEWS.md`.

## When you were started by GitHub (a Claude task, nobody in the chat)
The prompt may be as short as "Làm việc đang chờ trong repo này" ("do the work waiting in this repo"), and GitHub
adds a line such as "Phiếu văn học Đức số 3: giọng và ảnh đã sẵn sàng". Then: follow `AGENT_NIGHTLY.md` of this repo (its first check lists the `news-*` issues waiting for you), then `AGENT_NEWS.md`. Nobody answers questions, so do not ask; comments go on the issues
(🤖, Vietnamese).

## When the owner names a writer or a work (or pastes a script) in a chat
1. Create one issue in `maihaianh2911-bit/germany-news-video-factory`: title `[Văn học] <writer or work> —
   <main idea in Vietnamese>`, body with these sections (same names as the issue form):
   `### Nhà văn / tác phẩm (bắt buộc)` / `### Kịch bản (không bắt buộc)` = the owner's script exactly as pasted,
   or `_No response_` (then you write it, `AGENT_NEWS.md` §1.1) / `### Giọng đọc (không bắt buộc)` =
   `_No response_` unless the owner names a voice / `### Ghi chú (không bắt buộc)` = wishes from the chat. No
   labels: the workflow adds them (`news`, `news-plan`).
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
3. Give the owner the links to the video, the subtitles, the posting caption (`caption.txt`, written at the picks step, `AGENT_NEWS.md` §2.7) and the picture credits,
   and send the finished video file and its caption file in the chat. Send only finished videos: no previews,
   stills or progress pictures (owner, 18/11/2026, Japanese channel: "gửi video cuối cùng đã xong thôi, không cần gửi nhiều").

A script the owner sends is theirs: translate and split it, never edit its content (only exception: iron rule 2, a
script too short for 60 seconds). A script you write follows the sample (`AGENT_NEWS.md` §1.1), speaks as a German to
Germans and only states facts you are sure of. Look at the pictures yourself, preview before rendering.

## Changing the pipeline
Before pushing to `main`: `python3 tests/news_units.py`, `python3 tests/news_smoke.py --still`,
`python3 -m compileall -q scripts tests`, `npm run check`. They need
`pip install numpy scipy pillow num2words==0.5.14` (when `num2words` cannot build its `docopt` dependency:
`pip install docopt-ng && pip install --no-deps num2words==0.5.14`), `ffmpeg` (or `pip install imageio-ffmpeg==0.8.1`)
and `npm ci`; the first `--still` downloads Chrome Headless Shell (~110 MB). `check.yml` runs the same on GitHub.
Never touch secrets. Comments posted on GitHub start with 🤖 (they come from the owner's account).
No pull requests unless asked.
