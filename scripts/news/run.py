#!/usr/bin/env python3
"""Machine steps of a news video (GitHub Actions). Usage: run.py <N> <step> [<step> ...]

  prepare  voice (one 11labs job per line, unchanged lines reused), voice check, image search round 1
           (only when the queries changed) → renders/news/<N>/voice/, img/1/
  search   every news/<N>/search-<r>.json whose round is not on renders yet → renders/news/<N>/img/<r>/
  render   pictures from picks.json, plan, fonts, Remotion render, loudness, shot sheet
           → renders/news/<N>/video.mp4, subtitles.srt, credits.txt, sheet.jpg
After prepare/search the issue waits for Claude (news-pick) unless picks.json exists, then render runs too.
Needs GH_TOKEN, GITHUB_REPOSITORY; prepare needs VN11_API_KEY.
"""
import json, os, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import ff

N, steps = sys.argv[1], sys.argv[2:]
JOB = os.path.join(ROOT, 'news', N)
WORK = os.path.join(ROOT, 'out', f'news-{N}')          # mirror of renders/news/<N>/ for this run
PUB = os.path.join(ROOT, 'public')
REPO = os.environ['GITHUB_REPOSITORY']
URL = f"https://x-access-token:{os.environ['GH_TOKEN']}@github.com/{REPO}.git"
sh = lambda *a, **k: subprocess.run(a, check=True, **k)


def gh(*a):
    return subprocess.run(['gh', *a], check=False, capture_output=True, text=True)


def labels(add=(), remove=()):
    for l in remove: gh('issue', 'edit', N, '--remove-label', l)
    if add: gh('issue', 'edit', N, '--add-label', ','.join(add))


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


def publish(paths, msg):
    """Copy WORK-relative paths (files or folders) to renders/news/<N>/ in one commit."""
    wt = os.path.join(ROOT, 'out', 'renders-wt'); shutil.rmtree(wt, ignore_errors=True)
    subprocess.run(['git', 'worktree', 'prune'], cwd=ROOT)
    if subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, '+refs/heads/renders:refs/remotes/origin/renders'], cwd=ROOT).returncode == 0:
        sh('git', 'worktree', 'add', '-q', '--detach', wt, 'origin/renders', cwd=ROOT)
    else:   # new repo: the renders branch does not exist yet → start it empty
        sh('git', 'worktree', 'add', '-q', '--detach', wt, cwd=ROOT)
        sh('git', 'checkout', '-q', '--orphan', 'renders-new', cwd=wt)
        subprocess.run(['git', 'rm', '-rf', '-q', '.'], cwd=wt); sh('git', 'clean', '-fdq', cwd=wt)
    for p in paths:
        src, dst = os.path.join(WORK, p), os.path.join(wt, 'news', N, p)
        if os.path.isdir(src): shutil.copytree(src, dst, dirs_exist_ok=True)
        else: os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst)
    sh('git', '-c', 'user.name=render-bot', '-c', 'user.email=render-bot@users.noreply.github.com', 'add', '-A', cwd=wt)
    subprocess.run(['git', '-c', 'user.name=render-bot', '-c', 'user.email=render-bot@users.noreply.github.com', 'commit', '-q', '-m', f'news/{N}: {msg}'], cwd=wt)
    for i in range(4):
        if subprocess.run(['git', 'push', '-q', URL, 'HEAD:renders'], cwd=wt).returncode == 0:
            print(f'published news/{N}: {msg}'); return
        subprocess.run(['git', 'fetch', '-q', '--depth', '1', URL, 'renders'], cwd=wt)
        subprocess.run(['git', '-c', 'user.name=render-bot', '-c', 'user.email=render-bot@users.noreply.github.com', 'rebase', '-q', 'FETCH_HEAD'], cwd=wt)
    raise SystemExit('không đẩy được lên nhánh renders')


def link(p):
    return f'https://github.com/{REPO}/blob/renders/news/{N}/{p}'


def prepare():
    script = json.load(open(os.path.join(JOB, 'script.json'), encoding='utf-8'))
    labels(add=['news-voice'], remove=['news-plan', 'news-failed'])
    prev = os.path.join(WORK, 'voice')
    new = os.path.join(ROOT, 'out', f'voice-{N}')
    shutil.rmtree(new, ignore_errors=True)
    sh(sys.executable, os.path.join(HERE, 'tts_lines.py'), os.path.join(JOB, 'script.json'), new, '--prev', prev)
    sh(sys.executable, os.path.join(HERE, 'voice_check.py'), new, os.path.join(new, 'check.md'))
    shutil.rmtree(prev, ignore_errors=True); shutil.copytree(new, prev)
    paths = ['voice']
    q = script.get('queries') or []
    old = os.path.join(WORK, 'img', '1', 'queries.json')
    if q and (not os.path.exists(old) or json.load(open(old, encoding='utf-8')) != q):
        d = os.path.join(WORK, 'img', '1'); shutil.rmtree(d, ignore_errors=True)
        sh(sys.executable, os.path.join(ROOT, 'scripts', 'find_images.py'), d, *q)
        json.dump(q, open(os.path.join(d, 'queries.json'), 'w', encoding='utf-8'), ensure_ascii=False)
        paths.append('img/1')
    publish(paths, 'giọng đọc + ảnh')
    rows = json.load(open(os.path.join(prev, 'lines.json'), encoding='utf-8'))
    return rows


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
    ff.run('-i', os.path.join(out, 'raw.mp4'), '-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-pix_fmt', 'yuv420p',
           '-af', 'loudnorm=I=-15:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000', '-movflags', '+faststart', os.path.join(WORK, 'video.mp4'))
    sh(sys.executable, os.path.join(HERE, 'sheet.py'), os.path.join(WORK, 'video.mp4'), os.path.join(out, 'plan.json'), picks, os.path.join(WORK, 'sheet.jpg'))
    for f in ('subtitles.srt', 'credits.txt', 'plan.json'): shutil.copy(os.path.join(out, f), os.path.join(WORK, f))
    publish(['video.mp4', 'sheet.jpg', 'subtitles.srt', 'credits.txt', 'plan.json'], 'video')
    plan = json.load(open(os.path.join(out, 'plan.json'), encoding='utf-8'))
    return plan['duration']


def wake(why):
    subprocess.run(['bash', os.path.join(ROOT, 'scripts', 'wake_claude.sh'), why])


if __name__ == '__main__':
    fetch_renders()
    if 'prepare' in steps:
        rows = prepare()
        flagged = sum(1 for r in rows if r.get('diff'))
        speech = sum(r['duration'] for r in rows)
        if not os.path.exists(os.path.join(JOB, 'picks.json')):
            labels(add=['news-pick'], remove=['news-voice'])
            comment(f'🤖 Giọng đọc xong: {len(rows)} câu, {speech:.0f} giây lời đọc'
                    f'{f" ({flagged} câu cần Claude nghe lại cách đọc)" if flagged else ""}. Ảnh đã tìm xong. Claude sẽ chọn ảnh cho từng ý.')
            wake(f'Phiếu tin tức số {N}: giọng và ảnh đã sẵn sàng, chờ chọn ảnh.')
        elif 'render' not in steps:
            steps.append('render')
    if 'search' in steps:
        search()
        if 'render' not in steps:
            labels(add=['news-pick'], remove=['news-voice'])
    if 'render' in steps:
        if not os.path.exists(os.path.join(WORK, 'voice', 'lines.json')):
            raise SystemExit('chưa có giọng đọc cho phiếu này (cần script.json)')
        length = render()
        labels(add=['news-check'], remove=['news-render', 'news-voice'])
        m, s = divmod(round(length), 60)
        comment(f'🤖 Đã dựng xong bản video ({m} phút {s:02d} giây). Claude đang kiểm tra lại từng cảnh trước khi giao.\n\n'
                f'- Video: {link("video.mp4")}\n- Ảnh các cảnh: {link("sheet.jpg")}')
        wake(f'Phiếu tin tức số {N}: video đã dựng, chờ kiểm tra.')
