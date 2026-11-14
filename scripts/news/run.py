#!/usr/bin/env python3
"""Machine steps of a news video (GitHub Actions). Usage: run.py <N> <step> [<step> ...]

  prepare  voice (one 11labs job per line, unchanged lines reused), voice check, image search round 1
           (only when the queries changed) → renders/news/<N>/voice/, img/1/
           The voice is published before it is checked, and when a line fails the finished lines are published
           as voice-partial/ and reused by the next run: audio that was paid for is never read twice.
  search   every news/<N>/search-<r>.json whose round is not on renders yet → renders/news/<N>/img/<r>/
  render   pictures from picks.json, plan, fonts, Remotion render, loudness, shot sheet
           → renders/news/<N>/video.mp4, subtitles.srt, credits.txt, sheet.jpg
After prepare/search the issue waits for Claude (news-pick, Claude is called) unless picks.json exists, then render
runs too; not when a search round the picks use was searched (again) in this run: with changed queries, or because
the old results are gone from renders (cleaned after 14 days), the numbers may now name other pictures, so Claude
must choose again. render refuses picks whose pictures are not on renders.
A video over 95 MB is encoded again at a bitrate that lands ~90 MB (GitHub refuses files over 100 MB).
Needs GH_TOKEN, GITHUB_REPOSITORY; prepare needs VN11_API_KEY.
"""
import json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ff, prep

N, steps = sys.argv[1], sys.argv[2:]
JOB = os.path.join(ROOT, 'news', N)
WORK = os.path.join(ROOT, 'out', f'news-{N}')          # mirror of renders/news/<N>/ for this run
PUB = os.path.join(ROOT, 'public')
REPO = os.environ['GITHUB_REPOSITORY']
URL = f"https://x-access-token:{os.environ['GH_TOKEN']}@github.com/{REPO}.git"
GIT = ['git', '-c', 'user.name=render-bot', '-c', 'user.email=render-bot@users.noreply.github.com']
sh = lambda *a, **k: subprocess.run(a, check=True, **k)


def gh(*a, tries=1):
    """gh call; a failure is printed (stderr), and retried once more when tries=2 (label changes)."""
    for i in range(tries):
        r = subprocess.run(['gh', *a], check=False, capture_output=True, text=True)
        if r.returncode == 0:
            return r
        print(f'gh {" ".join(a[:4])} failed ({r.returncode}): {r.stderr.strip()[:300]}', file=sys.stderr, flush=True)
        if i < tries - 1: time.sleep(5)
    return r


def labels(add=(), remove=()):
    """New labels first, then the old ones go: an API error halfway never leaves the issue without a step label."""
    if add: gh('issue', 'edit', N, '--add-label', ','.join(add), tries=2)
    for l in remove:
        if l not in add: gh('issue', 'edit', N, '--remove-label', l, tries=2)


def fetch_renders(tries=4):
    """Current renders/news/<N>/ → WORK (empty when nothing was published yet). Only a renders branch that does
    not exist counts as "nothing yet"; a branch that cannot be fetched stops the run: going on would read every
    line again (paid) and search the pictures again."""
    os.makedirs(WORK, exist_ok=True)
    for i in range(tries):
        if i: time.sleep(5 * i)
        head = subprocess.run(['git', 'ls-remote', '--exit-code', URL, 'refs/heads/renders'], cwd=ROOT, capture_output=True)
        if head.returncode == 2:   # new repo: no renders branch yet
            return
        if head.returncode == 0 and subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode == 0:
            break
        print(f'renders: could not fetch the branch (attempt {i + 1}/{tries})', file=sys.stderr, flush=True)
    else:
        raise SystemExit(f'không lấy được nhánh renders sau {tries} lần thử (lỗi mạng GitHub?): dừng để không tạo lại giọng đọc đã trả tiền. Chạy lại bước này sau.')
    ls = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'origin/renders', f'news/{N}/'], cwd=ROOT, capture_output=True, text=True).stdout
    if ls.strip():
        tar = subprocess.run(['git', 'archive', 'origin/renders', f'news/{N}'], cwd=ROOT, capture_output=True, check=True).stdout
        tmp = os.path.join(ROOT, 'out', 'renders-tmp'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
        subprocess.run(['tar', '-x', '-C', tmp], input=tar, check=True)
        shutil.copytree(os.path.join(tmp, 'news', N), WORK, dirs_exist_ok=True)


def renders_worktree(wt):
    """A fresh worktree at the current tip of renders (an empty orphan when the branch does not exist yet).
    False when the branch could not be fetched."""
    shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', 'worktree', 'prune'], cwd=ROOT)
    head = subprocess.run(['git', 'ls-remote', '--exit-code', URL, 'refs/heads/renders'], cwd=ROOT, capture_output=True)
    if head.returncode == 2:   # new repo: start the branch empty
        sh('git', 'worktree', 'add', '-q', '--detach', wt, cwd=ROOT)
        sh('git', 'checkout', '-q', '--orphan', f'renders-new-{time.time_ns()}', cwd=wt)
        subprocess.run(['git', 'rm', '-rf', '-q', '.'], cwd=wt, capture_output=True); sh('git', 'clean', '-fdq', cwd=wt)
        return True
    if head.returncode or subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode:
        return False
    sh('git', 'worktree', 'add', '-q', '--detach', wt, 'origin/renders', cwd=ROOT)
    return True


def publish(paths, msg, tries=4, remove=()):
    """Copy WORK-relative paths (files or folders) to renders/news/<N>/ in one commit and push it; `remove` lists
    published paths to delete in the same commit. Every attempt
    starts again from the freshly fetched tip of renders (rebasing shallow history can conflict and then push a
    commit without this run's files). A folder replaces the published one, so no stale file stays next to a new
    index.json."""
    wt = os.path.join(ROOT, 'out', 'renders-wt')
    for i in range(tries):
        if i:
            print(f'renders: attempt {i}/{tries} failed (push rejected or fetch error), starting again from the new tip', file=sys.stderr, flush=True)
            time.sleep(5 * i)
        if not renders_worktree(wt):
            continue
        for p in paths:
            src, dst = os.path.join(WORK, p), os.path.join(wt, 'news', N, p)
            if os.path.isdir(src):
                shutil.rmtree(dst, ignore_errors=True); shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
        for p in remove:
            shutil.rmtree(os.path.join(wt, 'news', N, p), ignore_errors=True)
        sh(*GIT, 'add', '-A', cwd=wt)
        if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=wt).returncode == 0:
            print(f'news/{N}: {msg} — already published'); return
        sh(*GIT, 'commit', '-q', '-m', f'news/{N}: {msg}', cwd=wt)
        if subprocess.run(['git', 'push', '-q', URL, 'HEAD:refs/heads/renders'], cwd=wt).returncode == 0:
            print(f'published news/{N}: {msg}'); return
    raise SystemExit(f'không đẩy được lên nhánh renders sau {tries} lần thử ({msg})')


def link(p):
    return f'https://github.com/{REPO}/blob/renders/news/{N}/{p}'


def prepare():
    """Voice, then picture search round 1. Returns (lines.json rows, True when round 1 was searched in this run,
    True when round 1 was on renders before)."""
    script = json.load(open(os.path.join(JOB, 'script.json'), encoding='utf-8'))
    labels(add=['news-voice'], remove=['news-plan', 'news-failed'])
    prev = os.path.join(WORK, 'voice')
    part = os.path.join(WORK, 'voice-partial')   # lines finished by a run that failed halfway
    new = os.path.join(ROOT, 'out', f'voice-{N}')
    shutil.rmtree(new, ignore_errors=True)
    try:
        sh(sys.executable, os.path.join(HERE, 'tts_lines.py'), os.path.join(JOB, 'script.json'), new, '--prev', prev, '--prev', part)
    except subprocess.CalledProcessError:
        keep_partial_voice(new, part)
        raise
    shutil.rmtree(prev, ignore_errors=True); shutil.copytree(new, prev)
    had_part = os.path.isdir(part); shutil.rmtree(part, ignore_errors=True)
    # at once, before the check and the picture search: the paid voice is kept whatever fails afterwards
    publish(['voice'], 'giọng đọc', remove=['voice-partial'] if had_part else ())
    check = os.path.join(prev, 'check.md')
    try:
        sh(sys.executable, os.path.join(HERE, 'voice_check.py'), prev, check)
    except Exception as e:   # Whisper or its model download failed: the voice itself is fine and stays
        print(f'::warning::voice check failed ({type(e).__name__}: {e}): the voice is kept unchecked', flush=True)
        open(check, 'w', encoding='utf-8').write(
            '# Kiểm tra giọng đọc: CHƯA KIỂM TRA ĐƯỢC\n\nMáy nghe lại (Whisper) bị lỗi ở lượt này nên chưa có danh sách câu '
            'đáng ngờ. Giọng đọc vẫn được giữ. Claude: xem kỹ các câu có số, tên riêng và chữ viết tắt; muốn kiểm tra lại '
            'thì chạy lại bước `prepare` (các câu đã đọc được dùng lại, không tốn thêm ký tự).\n')
    publish(['voice'], 'kiểm tra giọng đọc')
    q = script.get('queries') or []
    old = os.path.join(WORK, 'img', '1', 'queries.json')
    had = os.path.exists(old)
    searched = False
    if q and (not had or json.load(open(old, encoding='utf-8')) != q):
        searched = True
        d = os.path.join(WORK, 'img', '1'); shutil.rmtree(d, ignore_errors=True)
        sh(sys.executable, os.path.join(ROOT, 'scripts', 'find_images.py'), d, *q)
        json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        publish(['img/1'], 'ảnh')
    rows = json.load(open(os.path.join(prev, 'lines.json'), encoding='utf-8'))
    return rows, searched, had


def keep_partial_voice(new, part):
    """A voice line failed: publish the lines that are finished (voice-partial/) so the next run reuses them."""
    try:
        if not os.path.exists(os.path.join(new, 'lines.json')) or not json.load(open(os.path.join(new, 'lines.json'), encoding='utf-8')):
            return
        for d in os.listdir(new):
            if d.startswith('job_'): shutil.rmtree(os.path.join(new, d), ignore_errors=True)
        shutil.rmtree(part, ignore_errors=True); shutil.copytree(new, part)
        publish(['voice-partial'], 'giọng đọc dở (các câu đã đọc xong, dùng lại ở lượt sau)')
    except BaseException as e:   # the voice error is the one to report
        print(f'::warning::could not keep the finished voice lines: {type(e).__name__}: {e}', flush=True)


def search():
    did = []
    for f in sorted(os.listdir(JOB)):
        if f.startswith('search-') and f.endswith('.json'):
            r = f[len('search-'):-len('.json')]
            q = json.load(open(os.path.join(JOB, f), encoding='utf-8'))['queries']
            d = os.path.join(WORK, 'img', r)
            if os.path.exists(os.path.join(d, 'queries.json')) and json.load(open(os.path.join(d, 'queries.json'), encoding='utf-8')) == q:
                continue
            shutil.rmtree(d, ignore_errors=True)
            earlier = [os.path.join(WORK, 'img', x) for x in sorted(os.listdir(os.path.join(WORK, 'img'))) if x != r] \
                if os.path.isdir(os.path.join(WORK, 'img')) else []
            sh(sys.executable, os.path.join(ROOT, 'scripts', 'find_images.py'), d, *q, env={**os.environ, 'FIND_SEEN': ':'.join(earlier)})
            json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
            did.append(f'img/{r}')
    if did: publish(did, 'tìm thêm ảnh')
    return [d[len('img/'):] for d in did]


GONE = ('picks.json dùng {n} ảnh không có trên nhánh renders ({files}). Ảnh tìm trước đây đã được dọn (video cũ quá 14 '
        'ngày) hoặc đợt tìm đó chưa chạy. Không dựng bằng ảnh đoán: chạy lại bước tìm ảnh (prepare cho đợt 1, search cho '
        'các đợt sau) rồi CHỌN LẠI ảnh, vì số ảnh của lần tìm mới có thể khác lần trước.')
NO_VOICE = ('chưa có giọng đọc của phiếu này trên nhánh renders (chưa tạo, hoặc đã được dọn vì video cũ quá 14 ngày). '
            'Chạy bước prepare trước (đẩy lại script.json hoặc Run workflow với steps = prepare).')
MAX_MB, TARGET_MB = 95, 90   # GitHub refuses files over 100 MB


def encode(raw, dst, rate):
    """Final encode of the Remotion output: H.264 + loudness-normalised AAC. rate = ['-crf', …] or a bitrate."""
    ff.run('-i', raw, '-c:v', 'libx264', '-preset', 'medium', *rate, '-pix_fmt', 'yuv420p',
           '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart', dst)


def render():
    labels(add=['news-render'], remove=['news-pick', 'news-check', 'news-done', 'news-fix', 'news-failed'])
    pub = os.path.join(PUB, 'news', N); shutil.rmtree(pub, ignore_errors=True)
    shutil.copytree(os.path.join(WORK, 'voice'), os.path.join(pub, 'voice'))
    imgsrc = os.path.join(WORK, 'img')
    if os.path.isdir(os.path.join(JOB, 'own')):
        shutil.copytree(os.path.join(JOB, 'own'), os.path.join(imgsrc, 'own'), dirs_exist_ok=True)
    picks = os.path.join(JOB, 'picks.json')
    gone = prep.missing_sources(json.load(open(picks, encoding='utf-8')), imgsrc)
    if gone:
        raise SystemExit(GONE.format(n=len(gone), files=', '.join(gone[:6]) + (' …' if len(gone) > 6 else '')))
    sh(sys.executable, os.path.join(HERE, 'prep.py'), picks, imgsrc, os.path.join(pub, 'img'))
    out = os.path.join(ROOT, 'out', f'render-{N}')
    sh(sys.executable, os.path.join(HERE, 'build.py'), JOB, PUB, N, imgsrc, out)
    sh(sys.executable, os.path.join(HERE, 'fonts.py'), os.path.join(out, 'plan.json'), os.environ.get('FONTSOURCE', '/tmp/fontsource'), PUB)
    sh('npx', 'remotion', 'render', 'src/news/index.ts', 'NewsV', os.path.join(out, 'raw.mp4'), f'--props={os.path.join(out, "plan.json")}',
       '--gl=swiftshader', '--log=error', cwd=ROOT)
    plan = json.load(open(os.path.join(out, 'plan.json'), encoding='utf-8'))
    raw, video = os.path.join(out, 'raw.mp4'), os.path.join(WORK, 'video.mp4')
    encode(raw, video, ['-crf', '24'])
    mb = os.path.getsize(video) / 1e6
    if mb > MAX_MB:   # long videos only (~3 min 15 s and more at crf 24): an average bitrate that lands ~90 MB
        kbps = int(TARGET_MB * 8000 / plan['duration']) - 160
        print(f'video {mb:.1f} MB > {MAX_MB} MB (GitHub limit 100 MB): encoding again at {kbps} kbit/s', flush=True)
        encode(raw, video, ['-b:v', f'{kbps}k', '-maxrate', f'{kbps}k', '-bufsize', f'{2 * kbps}k'])
        mb = os.path.getsize(video) / 1e6
        print(f'video now {mb:.1f} MB', flush=True)
        if mb > 100: raise SystemExit(f'video {mb:.1f} MB, vẫn quá 100 MB')
    sh(sys.executable, os.path.join(HERE, 'sheet.py'), video, os.path.join(out, 'plan.json'), picks, os.path.join(WORK, 'sheet.jpg'))
    for f in ('subtitles.srt', 'credits.txt', 'plan.json'): shutil.copy(os.path.join(out, f), os.path.join(WORK, f))
    publish(['video.mp4', 'sheet.jpg', 'subtitles.srt', 'credits.txt', 'plan.json'], 'video')
    return plan['duration']


def voice_quota():
    """One sentence on the 11labs balance after this run's voice lines ('' when no line was read or it is unknown)."""
    try:
        n = json.load(open(os.path.join(WORK, 'voice', 'quota.json')))['remaining_quota']
        return quota_text(n)
    except Exception:
        return ''


def quota_text(n):
    s = f'Hạn mức giọng đọc còn khoảng {int(n):,} ký tự'.replace(',', '.')
    return s + (' — ⚠️ sắp hết, nên nạp thêm. ' if n < LOW_QUOTA else '. ')


LOW_QUOTA = 20000   # characters; a 3-minute video uses about 3,000


def wake(why, say='', then='', tail=''):
    """Call the Claude task and post the step's comment on the issue: `say` (what the machine did) + `then` (what
    Claude does next), or, when Claude could not be called, `say` + which button to press (scripts/news/wake.py)."""
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'wake_claude.sh'), why, f'--issue={N}',
                    f'--say={say}', f'--then={then}', f'--tail={tail}'])


def stale_rounds(searched, used):
    """Rounds searched in this run that the picks use, sorted: their numbers may now name other pictures."""
    return sorted(set(searched) & set(used), key=lambda r: (len(r), r))


def main():
    fetch_renders()
    woke = False   # Claude was already called for the news-pick wait (no second call for the same wait)
    has_picks = os.path.exists(os.path.join(JOB, 'picks.json'))
    used = prep.rounds_used(json.load(open(os.path.join(JOB, 'picks.json'), encoding='utf-8'))) if has_picks else set()
    if 'prepare' in steps:
        rows, searched, had = prepare()
        flagged = sum(1 for r in rows if r.get('diff'))
        unchecked = not all('score' in r for r in rows)   # the Whisper check did not run (see check.md)
        quota = voice_quota()
        speech = sum(r['duration'] for r in rows)
        # round 1 searched in this run: with changed queries, or because the old results were cleaned from renders.
        # Either way existing picks of round 1 may now point at other pictures.
        requeried = searched and has_picks and (had or '1' in used)
        if not has_picks or requeried:
            if 'render' in steps: steps.remove('render')
            labels(add=['news-pick'], remove=['news-voice'])
            why = ('Từ khóa tìm ảnh đã đổi' if had else 'Ảnh tìm trước đây không còn (video cũ đã được dọn) nên máy đã tìm lại')
            wake(f'Phiếu tin tức (Đức) số {N}: ' + ('ảnh đợt 1 đã được tìm lại, phải chọn lại ảnh.' if requeried
                                                     else 'giọng và ảnh đã sẵn sàng, chờ chọn ảnh.'),
                 say=f'🤖 Giọng đọc xong: {len(rows)} câu, {speech:.0f} giây lời đọc'
                     f'{f" ({flagged} câu cần nghe lại cách đọc)" if flagged else ""}'
                     f'{" (máy chưa nghe lại được để kiểm tra cách đọc)" if unchecked else ""}. {quota}'
                     + (f'{why}: ảnh đợt 1 là ảnh mới, phải chọn lại ảnh trước khi dựng video.'
                        if requeried else 'Ảnh đã tìm xong.'),
                 then='Claude sẽ chọn lại ảnh.' if requeried else 'Claude sẽ chọn ảnh cho từng ý.')
            woke = True
        elif 'render' not in steps:
            steps.append('render')
    if 'search' in steps:
        rounds = search()
        stale = stale_rounds(rounds, used)
        if stale and 'render' in steps:
            steps.remove('render')   # never render old picks against pictures that were just searched again
        if 'render' not in steps and rounds:
            # one step label only: new pictures wait for Claude's choice, whatever the issue was before (a search
            # pushed during a fix or after the video was done used to leave news-pick next to news-done/news-fix)
            labels(add=['news-pick'], remove=['news-voice', 'news-check', 'news-done', 'news-fix', 'news-failed'])
            if not woke:
                # Claude may have stopped polling for the new round: call it so the issue does not wait at news-pick
                wake(f'Phiếu tin tức (Đức) số {N}: đã tìm thêm ảnh (đợt {", ".join(rounds)}), chờ chọn ảnh.',
                     say=f'🤖 Đã tìm thêm ảnh (đợt {", ".join(rounds)}).'
                         + (f' Ảnh đã chọn trước đây lấy từ đợt {", ".join(stale)} vừa được tìm lại, nên phải chọn lại ảnh trước khi dựng video.' if stale else ''),
                     then='Claude sẽ chọn lại ảnh.' if stale else 'Claude sẽ chọn ảnh cho từng ý.')
    if 'render' in steps:
        if not os.path.exists(os.path.join(WORK, 'voice', 'lines.json')):
            raise SystemExit(NO_VOICE)
        length = render()
        labels(add=['news-check'], remove=['news-render', 'news-voice'])
        m, s = divmod(round(length), 60)
        wake(f'Phiếu tin tức (Đức) số {N}: video đã dựng, chờ kiểm tra.',
             say=f'🤖 Đã dựng xong bản video ({m} phút {s:02d} giây).',
             then='Claude sẽ kiểm tra lại từng cảnh trước khi giao.',
             tail=f'- Video: {link("video.mp4")}\n- Ảnh các cảnh: {link("sheet.jpg")}')


if __name__ == '__main__':
    try:
        main()
    except SystemExit as e:   # a reason written for people: the workflow puts it in the issue comment
        if isinstance(e.code, str):
            open(f'/tmp/news-fail-{N}.txt', 'w', encoding='utf-8').write(e.code)
        raise
