#!/usr/bin/env python3
"""Machine steps of a news video (GitHub Actions). Usage: run.py <N> <step> [<step> ...]

  prepare  voice (one 11labs job per line, unchanged lines reused), voice check, image search round 1
           (only when the queries changed) → renders/news/<N>/voice/, img/1/
  search   every news/<N>/search-<r>.json whose round is not on renders yet → renders/news/<N>/img/<r>/
  render   pictures from picks.json, plan, fonts, Remotion render, loudness, shot sheet
           → renders/news/<N>/video.mp4, subtitles.srt, credits.txt, sheet.jpg
After prepare/search the issue waits for Claude (news-pick, Claude is called) unless picks.json exists, then render
runs too; not when prepare searched round 1 again with changed queries (the picks would point at other pictures).
A video over 95 MB is encoded again at a bitrate that lands ~90 MB (GitHub refuses files over 100 MB).
Needs GH_TOKEN, GITHUB_REPOSITORY; prepare needs VN11_API_KEY.
"""
import json, os, shutil, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ff

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


def comment(body):
    gh('issue', 'comment', N, '--body', body)


def fetch_renders():
    """Current renders/news/<N>/ → WORK (empty when nothing was published yet)."""
    os.makedirs(WORK, exist_ok=True)
    if subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode:
        return
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


def publish(paths, msg, tries=4):
    """Copy WORK-relative paths (files or folders) to renders/news/<N>/ in one commit and push it. Every attempt
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
    """Voice, then picture search round 1. Returns (lines.json rows, True when round 1 was searched again with
    changed queries, i.e. the pictures behind existing picks changed)."""
    script = json.load(open(os.path.join(JOB, 'script.json'), encoding='utf-8'))
    labels(add=['news-voice'], remove=['news-plan', 'news-failed'])
    prev = os.path.join(WORK, 'voice')
    new = os.path.join(ROOT, 'out', f'voice-{N}')
    shutil.rmtree(new, ignore_errors=True)
    sh(sys.executable, os.path.join(HERE, 'tts_lines.py'), os.path.join(JOB, 'script.json'), new, '--prev', prev)
    sh(sys.executable, os.path.join(HERE, 'voice_check.py'), new, os.path.join(new, 'check.md'))
    shutil.rmtree(prev, ignore_errors=True); shutil.copytree(new, prev)
    publish(['voice'], 'giọng đọc')   # before the picture search: the paid voice is kept even if the search fails
    q = script.get('queries') or []
    old = os.path.join(WORK, 'img', '1', 'queries.json')
    had = os.path.exists(old)
    requeried = False
    if q and (not had or json.load(open(old, encoding='utf-8')) != q):
        requeried = had
        d = os.path.join(WORK, 'img', '1'); shutil.rmtree(d, ignore_errors=True)
        sh(sys.executable, os.path.join(ROOT, 'scripts', 'find_images.py'), d, *q)
        json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        publish(['img/1'], 'ảnh')
    rows = json.load(open(os.path.join(prev, 'lines.json'), encoding='utf-8'))
    return rows, requeried


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


def wake(why):
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'wake_claude.sh'), why])


if __name__ == '__main__':
    fetch_renders()
    woke = False   # Claude was already called for the news-pick wait (no second call for the same wait)
    if 'prepare' in steps:
        rows, requeried = prepare()
        flagged = sum(1 for r in rows if r.get('diff'))
        speech = sum(r['duration'] for r in rows)
        has_picks = os.path.exists(os.path.join(JOB, 'picks.json'))
        requeried = requeried and has_picks
        if not has_picks or requeried:
            # changed round-1 queries renumber the pictures: existing picks would now point at other pictures
            if 'render' in steps: steps.remove('render')
            labels(add=['news-pick'], remove=['news-voice'])
            comment(f'🤖 Giọng đọc xong: {len(rows)} câu, {speech:.0f} giây lời đọc'
                    f'{f" ({flagged} câu cần Claude nghe lại cách đọc)" if flagged else ""}. '
                    + ('Từ khóa tìm ảnh đã đổi nên ảnh đợt 1 là ảnh mới: Claude phải chọn lại ảnh trước khi dựng video.'
                       if requeried else 'Ảnh đã tìm xong. Claude sẽ chọn ảnh cho từng ý.'))
            wake(f'Phiếu tin tức (Đức) số {N}: ' + ('từ khóa ảnh đợt 1 đã đổi, phải chọn lại ảnh.' if requeried
                                                     else 'giọng và ảnh đã sẵn sàng, chờ chọn ảnh.'))
            woke = True
        elif 'render' not in steps:
            steps.append('render')
    if 'search' in steps:
        rounds = search()
        if 'render' not in steps:
            labels(add=['news-pick'], remove=['news-voice'])
            if rounds and not woke:
                # Claude may have stopped polling for the new round: call it so the issue does not wait at news-pick
                comment(f'🤖 Đã tìm thêm ảnh (đợt {", ".join(rounds)}). Claude sẽ chọn ảnh cho từng ý.')
                wake(f'Phiếu tin tức (Đức) số {N}: đã tìm thêm ảnh (đợt {", ".join(rounds)}), chờ chọn ảnh.')
    if 'render' in steps:
        if not os.path.exists(os.path.join(WORK, 'voice', 'lines.json')):
            raise SystemExit('chưa có giọng đọc cho phiếu này (cần script.json)')
        length = render()
        labels(add=['news-check'], remove=['news-render', 'news-voice'])
        m, s = divmod(round(length), 60)
        comment(f'🤖 Đã dựng xong bản video ({m} phút {s:02d} giây). Claude đang kiểm tra lại từng cảnh trước khi giao.\n\n'
                f'- Video: {link("video.mp4")}\n- Ảnh các cảnh: {link("sheet.jpg")}')
        wake(f'Phiếu tin tức (Đức) số {N}: video đã dựng, chờ kiểm tra.')
