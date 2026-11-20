#!/usr/bin/env python3
"""Unit checks without network, Whisper or 11labs: the voice check's word comparison (numbers written out on both
sides), the whole-word readings sent to the voice, the call to the Claude task (fresh news-busy label, comment
wording, retries), and the picture search (query kinds, picture sizes, ranking, rate limit; made-up answers, no CLIP
model). Run from the repo root:
python3 tests/news_units.py   (needs num2words: pip install num2words==0.5.14)"""
import contextlib, datetime, io, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'news'))
from voice_check import compare
from tts_lines import spoken

flagged = lambda sent, heard: compare(sent, heard)[1]

# a wrong number is a misreading; the same number written in digits or in words is not
assert flagged('Inflation stands at 3.5 percent.', 'Inflation stands at three five percent.'), 'wrong decimal not flagged'
assert not flagged('Inflation stands at 3.5 percent.', 'Inflation stands at three point five percent.')
assert not flagged('Inflation stands at 3.5%.', 'Inflation stands at 3.5 percent.')
assert flagged('The reward rose to $14,000.', 'The reward rose to four thousand dollars.')
assert not flagged('The reward rose to $14,000.', 'The reward rose to fourteen thousand dollars.')
assert not flagged('He stole $5 million.', 'He stole five million dollars.')
assert not flagged('On November 12th, 1,000 people came.', 'On November twelfth, one thousand people came.')
assert not flagged('She was 23 years old in 1976.', 'She was twenty-three years old in nineteen seventy-six.')
assert not flagged('He came back in 2019. Then he left.', 'He came back in twenty nineteen. Then he left.')
assert not flagged('It cost 105 dollars.', 'It cost one hundred five dollars.')
assert not flagged("Emily's mother didn't know.", 'Emilys mother didnt know.')
# short words must match exactly, long ones may differ only by spelling
assert flagged('He was found guilty.', 'She was found guilty.')
assert flagged('The prosecution rested.', 'The persecution rested.')
assert not flagged('The neighbor called the police.', 'The neighbour called the police.')

# readings replace whole words only, longest first, each once
rd = {'US': 'U S', 'EZB': 'E Z B', 'E': 'Eh'}
assert spoken({'lines': ['Die USA und die US-Regierung, die EZB.']}, rd) == ['Die USA und die U S-Regierung, die E Z B.']
assert spoken({'lines': ['US', 'x'], 'tts': {'2': 'eigener Text'}}, rd) == ['U S', 'eigener Text']

# --- calling the Claude task (scripts/news/wake.py) ---
import wake
now = datetime.datetime(2026, 11, 14, 12, 0, tzinfo=datetime.timezone.utc)
assert wake.busy_fresh(['news', 'news-busy'], ['2026-11-14T08:00:00Z', '2026-11-14T10:30:00Z'], now)      # 1.5 h ago
assert not wake.busy_fresh(['news', 'news-busy'], ['2026-11-14T09:59:00Z'], now)                         # stale claim
assert not wake.busy_fresh(['news', 'news-pick'], ['2026-11-14T11:59:00Z'], now)                         # label removed
assert not wake.busy_fresh(['news-busy'], [], now) and not wake.busy_fresh(['news-busy'], ['?'], now)    # time unknown
# the comment promises Claude's next step only when Claude was called (or holds the issue)
ok = wake.body('🤖 Giọng đọc xong.', 'Claude sẽ chọn ảnh.', '- Video: x', True, '', '7', 'o/r')
assert ok == '🤖 Giọng đọc xong. Claude sẽ chọn ảnh.\n\n- Video: x', ok
no = wake.body('Giọng đọc xong.', 'Claude sẽ chọn ảnh.', '', False, wake.NO_ANSWER, '7', 'o/r')
assert no.startswith('🤖 Giọng đọc xong. ⚠️ Chưa gọi được Claude') and 'Claude sẽ' not in no, no
assert 'https://github.com/o/r/actions/workflows/wake.yml' in no and 'số 7' in no
assert wake.body('', '', '', True, '', '7', 'o/r') == '' and wake.body('', '', '', False, wake.NO_SECRET, '7', 'o/r').startswith('🤖 ⚠️')
# three tries on 429/5xx/network errors, one on a wrong token, none without the secrets
env = dict(os.environ)
quiet = contextlib.redirect_stdout(io.StringIO()); quiet.__enter__()   # the ::warning:: lines are not for the CI log
os.environ.pop('CLAUDE_TASK_URL', None); os.environ.pop('CLAUDE_TASK_TOKEN', None); os.environ.pop('GITHUB_STEP_SUMMARY', None)
assert wake.call('x', post=lambda *a: 1 / 0) == wake.NO_SECRET
os.environ.update(CLAUDE_TASK_URL='https://example.invalid/fire', CLAUDE_TASK_TOKEN='t')
def fake(codes):
    seen = []
    def post(url, token, payload):
        seen.append(payload); return codes[len(seen) - 1], '{"claude_code_session_url": "s"}'
    return seen, post
seen, post = fake([503, 0, 200]); assert wake.call('x' * 400, post=post, sleep=lambda s: None) == '' and len(seen) == 3
assert len(seen[0]) < 330                                                    # the reason is cut to 300 characters
seen, post = fake([429, 502, 504]); assert wake.call('x', post=post, sleep=lambda s: None) == wake.NO_ANSWER and len(seen) == 3
seen, post = fake([401, 200]); assert wake.call('x', post=post, sleep=lambda s: None) == wake.NO_ANSWER and len(seen) == 1
quiet.__exit__(None, None, None)
os.environ.clear(); os.environ.update(env)

# --- paid voice is never lost (scripts/vn11.py, scripts/news/tts_lines.py) ---
import argparse, json, shutil, tempfile, urllib.error
import tts_lines, vn11
tmp = tempfile.mkdtemp(prefix='news-units-')
quiet = contextlib.redirect_stdout(io.StringIO()); quiet.__enter__()
real = (vn11.req, vn11.download, vn11.time.sleep, tts_lines.ff.run, tts_lines.ff.duration, vn11.cmd_tts)
try:
    # one job: balance unreadable (before: network error, after: 500), 429 on create, 502 and a timeout while polling
    calls = []
    answers = {'POST': [(429, {}), (200, {'job_id': 'j1'})],
               'status': [(502, {}), TimeoutError(), (200, {'status': 'processing'}), (200, {'status': 'completed', 'download_url': 'u'})],
               'user': [urllib.error.URLError('down'), (500, {'error': 'x'})]}
    def req(method, path, **k):
        key = 'POST' if method == 'POST' else 'status' if path.startswith('status') else 'user'
        calls.append(key); r = answers[key].pop(0)
        if isinstance(r, Exception): raise r
        return r
    vn11.req = req; vn11.time.sleep = lambda s: None
    vn11.download = lambda url, dest, tries=4: open(dest, 'wb').write(b'mp3') or 3
    open(os.path.join(tmp, 't.txt'), 'w', encoding='utf-8').write('Guten Abend.')
    u = vn11.cmd_tts(argparse.Namespace(text_file=os.path.join(tmp, 't.txt'), out=os.path.join(tmp, 'job'), voice='clone_1', speed=1.0, timeout=60))
    assert u['job_id'] == 'j1' and u['remaining_quota'] is None and u['quota_used_this_job'] is None, u
    assert calls.count('POST') == 2 and calls.count('status') == 4 and not any(answers.values()), calls
    # a 502 on create is not sent again (the job may exist and be billed): the line fails
    answers['POST'] = [(502, {'error': 'bad gateway'}), (200, {'job_id': 'j2'})]; answers['user'] = [(200, {'remaining_quota': 9})]
    try: vn11.cmd_tts(argparse.Namespace(text_file=os.path.join(tmp, 't.txt'), out=os.path.join(tmp, 'job'), voice='clone_1', speed=1.0, timeout=60)); raise AssertionError('502 on create accepted')
    except SystemExit: pass
    assert len(answers['POST']) == 1

    # a line that fails keeps the finished lines; the next run reads only what is missing
    script = os.path.join(tmp, 'script.json')
    json.dump({'voice': 'clone_1', 'lines': ['Eins.', 'Zwei.', 'Drei.', 'Vier.']}, open(script, 'w'))
    read, fail_at = [], {'Drei.'}
    def cmd_tts(a):
        t = open(a.text_file, encoding='utf-8').read()
        if t in fail_at: vn11.die('11labs job failed')
        read.append(t); open(os.path.join(a.out, 'voice.mp3'), 'wb').write(t.encode())
        return {'remaining_quota': 1000 - len(read)}
    vn11.cmd_tts = cmd_tts
    tts_lines.ff.run = lambda *a: shutil.copy(a[1], a[-1]); tts_lines.ff.duration = lambda p: 1.0
    d1, d2, d3 = (os.path.join(tmp, x) for x in ('run1', 'run2', 'run3'))
    try: tts_lines.main([script, d1, '--prev', os.path.join(tmp, 'none')]); raise AssertionError('failed line not reported')
    except SystemExit: pass
    rows = json.load(open(os.path.join(d1, 'lines.json'), encoding='utf-8'))
    assert [r['text'] for r in rows] == ['Eins.', 'Zwei.'] and sorted(os.listdir(d1)) == ['line_01.mp3', 'line_02.mp3', 'lines.json', 'quota.json'], os.listdir(d1)
    read.clear(); fail_at.clear()
    tts_lines.main([script, d2, '--prev', os.path.join(tmp, 'none'), '--prev', d1])        # voice/ missing, voice-partial/ = d1
    rows = json.load(open(os.path.join(d2, 'lines.json'), encoding='utf-8'))
    assert read == ['Drei.', 'Vier.'] and [r['file'] for r in rows] == [f'line_0{i}.mp3' for i in (1, 2, 3, 4)], read
    assert open(os.path.join(d2, 'line_02.mp3'), 'rb').read() == b'Zwei.' and json.load(open(os.path.join(d2, 'quota.json'))) == {'remaining_quota': 998}
    read.clear()
    json.dump({'voice': 'clone_1', 'lines': ['Null.', 'Zwei.', 'Eins.']}, open(script, 'w'))   # reordered and changed: reuse by text
    tts_lines.main([script, d3, '--prev', d2])
    assert read == ['Null.'] and open(os.path.join(d3, 'line_03.mp3'), 'rb').read() == b'Eins.' and os.path.exists(os.path.join(d3, 'quota.json'))
finally:
    vn11.req, vn11.download, vn11.time.sleep, tts_lines.ff.run, tts_lines.ff.duration, vn11.cmd_tts = real
    quiet.__exit__(None, None, None); shutil.rmtree(tmp, ignore_errors=True)

# --- run.py helpers (imported with a made-up issue number; nothing runs at import) ---
os.environ.setdefault('GITHUB_REPOSITORY', 'owner/repo'); os.environ.setdefault('GH_TOKEN', 'x')
argv, sys.argv = sys.argv, ['run.py', '0']
import run
sys.argv = argv
assert run.quota_text(139448) == 'Hạn mức giọng đọc còn khoảng 139.448 ký tự. '
assert 'sắp hết' in run.quota_text(19999) and 'sắp hết' not in run.quota_text(20000)
# picks whose pictures were searched again (changed queries, or old results cleaned from renders) are not rendered
import prep
picks = {'images': {'a': {'src': '1/2-1.jpg'}, 'b': {'src': '3/1-1.jpg'}, 'c': {'src': 'own/foto.jpg'}, 'd': {'src': '10/1-1.jpg'}}}
assert prep.rounds_used(picks) == {'1', '3', '10'} and prep.rounds_used({'images': {'c': {'src': 'own/x.jpg'}}}) == set()
assert run.stale_rounds(['10', '2', '3'], prep.rounds_used(picks)) == ['3', '10'] and run.stale_rounds(['2'], prep.rounds_used(picks)) == []
tmp = tempfile.mkdtemp(prefix='news-units-')
os.makedirs(os.path.join(tmp, '1')); os.makedirs(os.path.join(tmp, 'own'))
for f in ('1/2-1.jpg', 'own/foto.jpg'): open(os.path.join(tmp, f), 'w').close()
assert prep.missing_sources(picks, tmp) == ['3/1-1.jpg', '10/1-1.jpg']
assert '2 ảnh' in run.GONE.format(n=2, files='3/1-1.jpg, 10/1-1.jpg') and 'CHỌN LẠI' in run.GONE
shutil.rmtree(tmp, ignore_errors=True)
# --- the catalogue of moves (scripts/news/moves.py) ---
import moves
assert 8 <= len(moves.MOVES) <= 12
for (w, h) in ((1600, 1100), (800, 1200), (1150, 1150), (2600, 900)):          # landscape, portrait, square, panorama
    for name in moves.MOVES:
        for d in (1.5, 4, 9):
            for f in (None, (0.1, 0.2), (0.9, 0.85)):
                a, b = moves.expand(name, w, h, d, f)
                for c in (a, b):   # the panel never looks past an edge of the picture
                    hx, hy = moves.half(w, h, c['z'])
                    assert 1.0 <= c['z'] <= 1.46 and hx - 1e-3 <= c['x'] <= 1 - hx + 1e-3 and hy - 1e-3 <= c['y'] <= 1 - hy + 1e-3, (name, w, h, d, f, c)
                assert a != b, (name, w, h, d, f)                               # every move moves
E = lambda n, d=5, f=None: moves.expand(n, 1600, 1100, d, f)
assert E('tien-gan')[0]['z'] == 1.0 and 1.08 <= E('tien-gan')[1]['z'] <= 1.2 and E('tien-gan', 9)[1]['z'] > E('tien-gan', 3)[1]['z']
assert E('chi-tiet')[1]['z'] >= 1.25 > E('tien-gan')[1]['z'] and E('lui-ra')[0]['z'] > E('lui-ra')[1]['z'] == 1.0
assert E('luot-phai')[0]['x'] < E('luot-phai')[1]['x'] and E('luot-trai')[0]['x'] > E('luot-trai')[1]['x'] and E('luot-phai')[0]['z'] == E('luot-phai')[1]['z']
assert E('nang-len')[0]['y'] > E('nang-len')[1]['y'] and E('ha-xuong')[0]['y'] < E('ha-xuong')[1]['y']
assert E('dung-yen')[1]['z'] <= 1.03 and abs(E('troi-nhe')[1]['x'] - E('troi-nhe')[0]['x']) < 0.15 and E('troi-nhe')[1]['z'] > E('troi-nhe')[0]['z']
assert abs(E('tien-gan', f=(0.3, 0.4))[1]['x'] - 0.3) < 0.08                    # ends on the subject
T = lambda n, d, w=1600, h=1100, f=None: moves.travel(*moves.expand(n, w, h, d, f), w, h)
for d in (2.2, 4, 9):                                                           # calm: never faster than the move's cap
    assert T('luot-phai', d)[0] <= moves.SPEED['luot-phai'][3] * d + 1e-3 and T('nang-len', d, 800, 1200)[1] <= moves.SPEED['nang-len'][3] * d + 1e-3
# short shots still visibly move: the least travel is kept (speed goes up), until the shot is too short for the move
assert T('luot-phai', 2.2)[0] >= 0.24 and T('nang-len', 2.2, 800, 1200)[1] >= 0.24 and T('troi-nhe', 2.2)[0] >= 0.11
assert E('tien-gan', 2.2)[1]['z'] >= 1.10 and E('lui-ra', 2.2)[0]['z'] >= 1.18 and E('chi-tiet', 2.2)[1]['z'] >= 1.25
assert not any(moves.too_short(n, 2.2) for n in moves.MOVES) and all(moves.too_short(n, 1.5) for n in moves.SPEED) and not moves.too_short('dung-yen', 1.0)
assert E('tien-gan', 1.2)[1]['z'] < 1.07                                        # too short: slower rather than a jerk
w15 = moves.warnings({'img': 'a', 'move': 'luot-phai'}, 1600, 1100, 1.5)
assert len(w15) == 1 and 'too short' in w15[0] and 'dung-yen' in w15[0] and moves.warnings({'img': 'a', 'move': 'luot-phai'}, 1600, 1100, 2.2) == []
assert moves.warnings({'img': 'a', 'move': 'luot-phai', 'from': {}, 'to': {}}, 1600, 1100, 1.0) == [] and moves.warnings({'img': 'a', 'from': {}, 'to': {}}, 1600, 1100, 1.0) == []
# a tilt on a landscape picture (no room at normal size) zooms in as far as needed and really travels
for d in (2.2, 5):
    a, b = moves.expand('nang-len', 1920, 1080, d)
    assert 1.2 <= a['z'] <= moves.MAX_SLIDE_Z and T('nang-len', d, 1920, 1080)[1] >= 0.24, (d, a, b)
assert T('ha-xuong', 5, 1920, 1080)[1] > T('ha-xuong', 2.2, 1920, 1080)[1] and moves.warnings({'img': 'a', 'move': 'nang-len'}, 1920, 1080, 4) == []
# chi-tiet / lui-ra: the subject is inside the frame at both ends (so during the whole move), also with "wide"
def inside(c, f, w, h, k=moves.KEEP + 0.01):
    hx, hy = moves.half(w, h, c['z']); return abs(f[0] - c['x']) <= k * hx + 1e-3 and abs(f[1] - c['y']) <= k * hy + 1e-3
for (w, h) in ((1920, 1080), (800, 1200), (2600, 900)):
    for f in ((0.05, 0.1), (0.6, 0.38), (0.95, 0.9)):
        for wide in (None, (0.2, 0.5), (0.9, 0.2)):
            for n in ('chi-tiet', 'lui-ra'):
                a, b = moves.expand(n, w, h, 4, f, wide)
                fc = moves.cam(w, h, max(a['z'], b['z']), *f)                   # the subject as the close end can show it
                assert inside(a if a['z'] == 1.0 else b, (fc['x'], fc['y']), w, h, 1.0), (n, w, h, f, wide, a, b)
lr = moves.expand('lui-ra', 1920, 1080, 6, (0.6, 0.38), (0.4, 0.45))[1]         # pulls back towards a second subject
assert lr['z'] == 1.0 and lr['x'] < moves.expand('lui-ra', 1920, 1080, 6, (0.6, 0.38))[1]['x'] and inside(lr, (0.6, 0.38), 1920, 1080)
far = moves.warnings({'img': 'a', 'move': 'lui-ra', 'focus': [0.6, 0.38], 'wide': [0.1, 0.4]}, 1920, 1080, 6)
assert len(far) == 1 and 'would lose the subject' in far[0] and moves.check({'img': 'a', 'move': 'lui-ra', 'wide': [3, 1]}, 'c') != []
try: moves.expand('zoom-nhanh', 1600, 1100, 5); raise AssertionError('unknown move accepted')
except ValueError as e: assert all(n in str(e) for n in moves.MOVES)
ok_shot = {'img': 'a', 'move': 'lui-ra', 'why': 'x', 'focus': [0.5, 0.4], 'fade': 0}
assert moves.check(ok_shot, 'cảnh 1-1') == [] and moves.check({'img': 'a', 'from': {}, 'to': {}}, 'c') == []
assert moves.check({'pair': {}}, 'c') == [] and len(moves.check({'pair': {}, 'move': 'lui-ra'}, 'c')) == 1
bad = moves.check({'img': 'a', 'move': 'zoom', 'focus': [2, 0], 'fade': 9}, 'cảnh 1-2')
assert len(bad) == 3 and 'tien-gan, chi-tiet' in bad[0] and bad[0].startswith('cảnh 1-2'), bad
assert 'cần "move"' in moves.check({'img': 'a', 'from': {}}, 'c')[0]
assert moves.camera({'move': 'tien-gan', 'to': {'z': 1.5, 'x': .5, 'y': .5}}, 1600, 1100, 5)[1]['z'] == 1.5       # explicit numbers win
assert moves.camera({'from': 1, 'to': 2}, 1600, 1100, 5) == (1, 2) and moves.label({'from': 1, 'to': 2}) == '-' and moves.label(ok_shot) == 'lui-ra'
# --- the posting caption (scripts/news/caption.py) ---
import caption
good = ("JonBenét Ramsey: the ransom note nobody can explain\n"
        "On December 26, 1996, a six-year-old girl was found dead in her family's home in Boulder, Colorado.\n"
        "Nearly thirty years later, the case is still open.\n\n"
        "#TrueCrime #JonBenetRamsey #ColdCase #Colorado #CrimeStory #shorts\n\n"
        "Image credits: Wikimedia Commons (see credits)\n")
assert caption.check(good) == [], caption.check(good)
assert caption.check(good.replace('JonBenét Ramsey: the', 'JonBenét Ramsey: ' + 'x' * 80))[0].startswith('tiêu đề dài')
assert any('hashtag' in b for b in caption.check(good.replace(' #Colorado #CrimeStory #shorts', '')))   # 3 tags
assert any('Image credits' in b for b in caption.check(good.replace('Image credits:', 'Photos:')))
assert any('tiếng Anh' in b for b in caption.check(good.replace('Nearly thirty', 'Gần ba mươi năm sau, vụ án')))      # Vietnamese
assert any('tiếng Anh' in b for b in caption.check(good.replace('Nearly thirty', '三十年近く')))                # Japanese
assert any('mô tả' in b for b in caption.check(good.split('\n')[0] + '\n\n#a #b #c #d #e\n\nBildquellen: x'))
assert any('2000' in b for b in caption.check(good.replace('Nearly thirty', 'Word. ' * 400 + 'Nearly thirty')))
assert caption.check('') == ['caption.txt trống'] and len(caption.check('Nur ein Titel')) == 1
# a caption-only run installs no tools: run.py must load without numpy and Pillow
import subprocess
blk = tempfile.mkdtemp(prefix='news-units-'); os.makedirs(os.path.join(blk, 'PIL'))
for f in ('numpy.py', os.path.join('PIL', '__init__.py')): open(os.path.join(blk, f), 'w').write('raise ImportError("not installed")\n')
r = subprocess.run([sys.executable, '-c', 'import sys; sys.argv = ["run.py", "0", "caption"]; import run'], capture_output=True, text=True,
                   env={**os.environ, 'PYTHONPATH': blk + os.pathsep + os.path.join(ROOT, 'scripts', 'news'), 'GITHUB_REPOSITORY': 'o/r', 'GH_TOKEN': 'x'})
assert r.returncode == 0, r.stderr[-500:]
shutil.rmtree(blk, ignore_errors=True)
# --- the picture search (scripts/find_images.py): made-up answers of Commons, Wikipedia and Wikidata, no CLIP model ---
import random, re, urllib.parse
from PIL import Image
sys.path.insert(0, os.path.join(ROOT, 'scripts'))
import find_images as F
F.LANGS = ('de', 'en')   # the mocked Wikipedias below are a two-language case (the channel itself reads only en)
# a query kind: wiki: and geo: are their own; everything else is a Commons search and stays whole
assert F.source_of('wiki: Friedrich Merz') == ('wiki', 'Friedrich Merz') and F.source_of(' Wiki:Bundestag ') == ('wiki', 'Bundestag')
assert F.source_of('geo: 52.5186,13.3762 300') == ('geo', '52.5186,13.3762 300')
for q in ('incategory:"Reichstag building" 2025', 'Dr. Müller: Akte', 'Frankfurt skyline'): assert F.source_of(q) == (None, q), q
assert F.KEYWORD.search('incategory:"Friedrich Merz" 2025') and not F.KEYWORD.search('Olaf Scholz 2024')
assert F.parts('Bundestag') == ('Bundestag', None, None) and F.parts({'q': 'attic', 'want': ' a dark attic ', 'keep': 12}) == ('attic', 'a dark attic', 12)
for bad in ({'want': 'x'}, {'q': 7}, {'q': 'x', 'keep': 0}, {'q': 'x', 'keep': '8'}, 7):
    try: F.parts(bad); raise AssertionError(f'query accepted: {bad}')
    except ValueError: pass
# Commons pictures are taken in the standard sizes: the largest up to 1920 px, a file under 960 px whole; the 330 px
# version is the preview; a licence that does not allow the video and a file that is no picture are left out; the
# title keeps its "File:" (build.py cuts it off for credits.txt)
def _pg(title, w, h, lic='CC BY-SA 4.0', mime='image/jpeg', i=0, thumb=None):
    name = title[5:].replace(' ', '_')
    return {'title': title, 'index': i, 'imageinfo': [{'mime': mime, 'width': w, 'height': h, 'descriptionurl': 'https://commons.wikimedia.org/wiki/File:' + name,
            'url': f'https://upload.wikimedia.org/wikipedia/commons/a/ab/{name}?utm=1',
            'thumburl': thumb or (f'https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/{name}/330px-{name}' if w > 330 else f'https://upload.wikimedia.org/wikipedia/commons/a/ab/{name}'),
            'extmetadata': {'LicenseShortName': {'value': lic}, 'Artist': {'value': '<a href="x">Foto  Graf</a>'}, 'DateTimeOriginal': {'value': '2025-02-23'}}}]}
res = F.results([_pg('File:Mid.jpg', 1400, 900, i=2), _pg('File:Big.jpg', 5100, 3000, i=1), _pg('File:Small.jpg', 640, 480, i=3), _pg('File:Tiny.jpg', 300, 300, i=4),
                 _pg('File:Press.jpg', 3000, 2000, lic='All rights reserved', i=5), _pg('File:Akte.pdf', 3000, 2000, mime='application/pdf', i=6),
                 _pg('File:Karte.tif', 4000, 3000, mime='image/tiff', i=7, thumb='https://thumb.wikimedia.org/wikipedia/commons/thumb/a/ab/Karte.tif/lossy-page1-330px-Karte.tif.jpg')])
assert [r['title'] for r in res] == ['File:Big.jpg', 'File:Mid.jpg', 'File:Small.jpg', 'File:Tiny.jpg', 'File:Karte.tif'], res
assert res[0]['thumb'].endswith('/1920px-Big.jpg') and res[0]['preview'].endswith('/330px-Big.jpg') and (res[0]['width'], res[0]['height']) == (5100, 3000), res[0]
assert res[1]['thumb'].endswith('/1280px-Mid.jpg') and res[2]['thumb'].endswith('/ab/Small.jpg') and res[2]['preview'].endswith('/330px-Small.jpg'), res[1:3]
assert res[3]['thumb'] == res[3]['preview'] and '?' not in res[3]['thumb'] and res[4]['thumb'].endswith('/lossy-page1-1920px-Karte.tif.jpg'), res[3:]
assert {'page', 'license', 'artist', 'credit', 'date', 'description', 'attribution_required', 'source'} <= set(res[0]) and res[0]['artist'] == 'Foto Graf' and res[0]['source'] == 'commons'
# a list of titles comes back in the order asked, not in the API's; long lists are asked in several requests
assert [r['title'] for r in F.results([_pg('File:B.jpg', 2000, 2000), _pg('File:A.jpg', 2000, 2000)], order=['File:A.jpg', 'File:B.jpg'])] == ['File:A.jpg', 'File:B.jpg']
assert [len(g) for g in F.batches([f'File:{i}.jpg' for i in range(120)])] == [50, 50, 20] and all(len(g) < 50 for g in F.batches(['File:' + 'ü' * 60 + f'{i}.jpg' for i in range(50)]))
assert F.ICON.search('File:Commons-logo.svg') and F.ICON.search('File:Flag of Germany.png') and not F.ICON.search('File:Friedrich Merz 2025.jpg')
try: F.geo('Reichstag', 5); raise AssertionError('geo: without coordinates must be refused')
except ValueError: pass
# a host that answers 429 is given the time it asks for (Retry-After), but 90 s in a whole run at most: after that a
# request to it is tried once; another host has its own count
real_net = (F.urllib.request.urlopen, F.time.sleep)
asked, waits = [], []
def refuse(req, timeout=None): asked.append(req.full_url); raise urllib.error.HTTPError(req.full_url, 429, 'Too Many Requests', {'Retry-After': '16'}, None)
try:
    F.urllib.request.urlopen = refuse; F.time.sleep = lambda s: waits.append(s); F.WAITED.clear()
    for n_asked, url in ((4, 'https://commons.wikimedia.org/w/api.php?a=1'), (3, 'https://commons.wikimedia.org/w/api.php?a=2'),
                         (1, 'https://commons.wikimedia.org/w/api.php?a=3'), (2, 'https://upload.wikimedia.org/x.jpg')):
        asked.clear(); waits.clear()
        try: F.get(url, tries=4 if 'api' in url else 2); raise AssertionError('429 accepted')
        except urllib.error.HTTPError: pass
        assert len(asked) == n_asked and [w for w in waits if w >= 1] == [16] * (n_asked - 1), (url, asked, waits)
    assert F.WAITED == {'commons.wikimedia.org': 80, 'upload.wikimedia.org': 16} and max(F.WAITED.values()) <= F.PATIENCE
    assert F.pause(urllib.error.HTTPError('u', 429, '', {}, None)) == 10 and F.pause(urllib.error.HTTPError('u', 429, '', {'Retry-After': '600'}, None)) == 30
finally:
    F.urllib.request.urlopen, F.time.sleep = real_net; F.WAITED.clear()

# a whole search with made-up answers: every request goes through fake_get (API answers as JSON, pictures as JPEG)
def _jpg(name, px):
    """A picture of its own for every name (same name = same picture in any size): 9×8 random grey blocks."""
    rnd = random.Random(name); im = Image.frombytes('L', (9, 8), bytes(rnd.sample(range(0, 256, 3), 72))).resize((px, px * 2 // 3), Image.NEAREST)
    b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=85); return b.getvalue()
LIB = {}       # search words -> pages; file title -> page (for titles=… requests)
WIKI = {}      # (host, a parameter that tells the request apart) -> answer
urls = []
def fake_get(url, tries=4, timeout=60):
    urls.append(url); u = urllib.parse.urlsplit(url); p = dict(urllib.parse.parse_qsl(u.query))
    if not u.path.endswith('api.php'):                                   # a picture: …/<width>px-<name> or the file itself
        name = urllib.parse.unquote(u.path.rsplit('/', 1)[-1]); m = re.match(r'(?:lossy-page1-)?(\d+)px-(.+)$', name)
        if 'kaputt' in name: raise urllib.error.URLError('connection reset')
        return _jpg(m.group(2) if m else name, int(m.group(1)) if m else 600)
    if p.get('generator') == 'search':
        if p['gsrsearch'] not in LIB: raise urllib.error.URLError('timed out')
        return json.dumps({'query': {'pages': {str(i): pg for i, pg in enumerate(LIB[p['gsrsearch']])}}}).encode()
    if p.get('generator') == 'geosearch':
        return json.dumps({'query': {'pages': {str(i): pg for i, pg in enumerate(LIB['geo ' + p['ggscoord']])}}}).encode()
    if p.get('prop') == 'imageinfo':                                      # titles=A|B|C, answered in another order
        return json.dumps({'query': {'pages': {str(i): LIB[t] for i, t in enumerate(reversed(p['titles'].split('|'))) if t in LIB}}}).encode()
    key = p.get('prop') or p.get('list') or p.get('action')
    return json.dumps(WIKI[(u.netloc, key, p.get('titles') or p.get('cmtitle', '') + p.get('cmtype', '') or p.get('ids') or p.get('search'))]).encode()
# 1) plain strings, ranking off: what the search always returned — the first 8 of 12 in the search's order, without
#    files under 400 px (250 px for incategory:), without second scans; a failed search keeps an "error"
LIB['Bundestag'] = [_pg(f'File:B{i:02d}.jpg', 3000, 2000, i=i) for i in range(1, 13)]
LIB['Bundestag'][1] = _pg('File:Winzig.jpg', 390, 2000, i=2)                                    # too small
LIB['Bundestag'][3] = _pg('File:B01.jpg', 1300, 867, i=4); LIB['Bundestag'][3]['title'] = 'File:B01 (Zweitscan).jpg'   # the same picture again, smaller
LIB['Bundestag'].reverse()                                                                     # the API's order is not the search's
LIB['incategory:"Friedrich Merz"'] = [_pg('File:Merz Flugblatt.jpg', 300, 260, i=1), _pg('File:Merz Marke.jpg', 240, 200, i=2), _pg('File:Merz kaputt.jpg', 2000, 3000, i=3)]
real_find = (F.get, F.picture, F.Clip.ready, F.Clip.scores, sys.argv, os.environ.get('FIND_RANK'), os.environ.get('FIND_SEEN'))
tmp = tempfile.mkdtemp(prefix='news-units-'); o1, o2 = os.path.join(tmp, '1'), os.path.join(tmp, '2')
said = io.StringIO(); quiet = contextlib.redirect_stdout(said); quiet.__enter__()
try:
    F.get = fake_get; os.environ['FIND_RANK'] = '0'; os.environ.pop('FIND_SEEN', None)
    sys.argv = ['find_images.py', o1, 'Bundestag', 'incategory:"Friedrich Merz"', 'Netz weg']
    F.main()
    idx = json.load(open(os.path.join(o1, 'index.json'), encoding='utf-8'))
    assert [(e['k'], e['query'], len(e['results'])) for e in idx] == [(1, 'Bundestag', 8), (2, 'incategory:"Friedrich Merz"', 1), (3, 'Netz weg', 0)], idx
    assert [r['title'] for r in idx[0]['results']] == [f'File:B{i:02d}.jpg' for i in (1, 3, 5, 6, 7, 8, 9, 10)], [r['title'] for r in idx[0]['results']]
    assert [r['file'] for r in idx[0]['results']] == [f'1-{n}.jpg' for n in range(1, 9)] and idx[0]['candidates'] == 11 and 'error' not in idx[0]
    assert all(r['thumb'].endswith('/1920px-' + r['title'][5:]) and r['page'].endswith(r['title'][5:]) and r['source'] == 'commons' for r in idx[0]['results'])
    assert not any(k in r for r in idx[0]['results'] for k in ('preview', 'rank', 'match', 'error')) and 'want' not in idx[0]
    assert idx[1]['results'][0]['title'] == 'File:Merz Flugblatt.jpg' and idx[1]['results'][0]['thumb'].endswith('/ab/Merz_Flugblatt.jpg')   # 260 px: kept for incategory:
    assert 'URLError' in idx[2]['error'] and sorted(os.listdir(o1)) == sorted([f'1-{n}.jpg' for n in range(1, 9)] + ['2-1.jpg', 'index.json', 'sheet_1.jpg', 'sheet_2.jpg'])
    assert Image.open(os.path.join(o1, '1-1.jpg')).size == (1920, 1280) and Image.open(os.path.join(o1, 'sheet_1.jpg')).size == (4 * 380, 2 * 410)
    asked = [dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(u).query)) for u in urls if 'generator=search' in u]
    assert [(a['gsrsearch'], a['gsrlimit'], a['gsrnamespace'], a['iiurlwidth']) for a in asked] == [(q, '12', '6', '330') for q in sys.argv[2:]], asked
    assert not any('/330px-' in u for u in urls)                         # no ranking: no small versions are fetched
    # every search failing is an error of the run
    sys.argv = ['find_images.py', os.path.join(tmp, 'x'), 'Netz weg', 'Netz ganz weg']
    try: F.main(); raise AssertionError('a run with every search failed must fail')
    except SystemExit as e: assert 'every search failed' in str(e.code)

    # 2) --spec: a query with a wish is ranked (CLIP made up here: a score for every file), wiki: reads one Wikidata
    #    item, a later round does not show pictures of an earlier one again (FIND_SEEN), a broken entry costs only itself
    LIB['Gerichtssaal'] = [_pg(f'File:G{c}.jpg', 2400, 1600, i=i) for i, c in enumerate('ABCDEF', 1)] + [_pg('File:B05.jpg', 3000, 2000, i=7)]
    fit = {'GA': 0.285, 'GB': 0.33, 'GC': 0.10, 'GD': 0.30, 'GE': 0.31, 'GF': 0.29, 'B05': 0.32}; unfit = {'GE': 0.25}
    texts = []
    def scores(cls, images, text):
        texts.append(text); names = [im.url.rsplit('px-', 1)[-1][:-4] for im in images]
        return [fit[n] for n in names], [unfit.get(n, 0.1) for n in names]
    def picture(url, **k):
        im = real_find[1](url, **k); im.url = url; return im
    F.picture = picture; F.Clip.ready = classmethod(lambda cls: True); F.Clip.scores = classmethod(scores)
    for t, (w, h) in {'File:Reichstag.jpg': (4000, 3000), 'File:Plenarsaal.jpg': (3000, 2000), 'File:Kuppel.jpg': (2000, 3000), 'File:Sitzung.jpg': (1000, 700),
                      'File:Stuhl.jpg': (800, 800), 'File:Briefmarke.jpg': (300, 380)}.items(): LIB[t] = _pg(t, w, h)
    LIB['geo 52.5186|13.3762'] = [_pg('File:Wiese 001.jpg', 3000, 2000, i=1), _pg('File:Wiese 002.jpg', 3000, 2000, i=2), _pg('File:Reichstag.jpg', 4000, 3000, i=3)]
    snak = lambda v: [{'mainsnak': {'datavalue': {'value': v}}}]
    WIKI.update({
        ('de.wikipedia.org', 'pageprops', 'Bundestag'): {'query': {'pages': {'9': {'title': 'Deutscher Bundestag', 'pageprops': {'wikibase_item': 'Q154797'}}}}},
        ('de.wikipedia.org', 'pageprops', 'Merz'): {'query': {'pages': {'8': {'title': 'Merz', 'pageprops': {'wikibase_item': 'Q1', 'disambiguation': ''}}}}},
        ('en.wikipedia.org', 'pageprops', 'Merz'): {'query': {'pages': {'-1': {'title': 'Merz', 'missing': ''}}}},
        ('www.wikidata.org', 'wbsearchentities', 'Merz'): {'search': []},
        ('www.wikidata.org', 'wbgetentities', 'Q154797'): {'entities': {'Q154797': {'id': 'Q154797',
            'labels': {'en': {'value': 'Bundestag'}, 'de': {'value': 'Deutscher Bundestag'}}, 'descriptions': {'de': {'value': 'Parlament der Bundesrepublik Deutschland'}},
            'claims': {'P18': snak('Reichstag.jpg'), 'P373': snak('Deutscher Bundestag'), 'P625': snak({'latitude': 52.5186, 'longitude': 13.3762})},
            'sitelinks': {'dewiki': {'title': 'Deutscher Bundestag'}, 'enwiki': {'title': 'Bundestag'}}}}},
        ('de.wikipedia.org', 'images', 'Deutscher Bundestag'): {'query': {'pages': {'9': {'images': [{'title': 'Datei:Plenarsaal.jpg'}, {'title': 'Datei:Commons-logo.svg'}, {'title': 'Datei:Reichstag.jpg'}, {'title': 'Datei:Nur in dewiki.jpg'}]}}}},
        ('en.wikipedia.org', 'images', 'Bundestag'): {'query': {'pages': {'7': {'images': [{'title': 'File:Kuppel.jpg'}, {'title': 'File:Plenarsaal.jpg'}, {'title': 'File:Flag of Germany.svg'}]}}}},
        ('commons.wikimedia.org', 'categorymembers', 'Category:Deutscher Bundestagfile'): {'query': {'categorymembers': [{'title': 'File:Sitzung.jpg'}, {'title': 'File:Kuppel.jpg'}, {'title': 'File:Briefmarke.jpg'}]}},
        ('commons.wikimedia.org', 'categorymembers', 'Category:Deutscher Bundestagsubcat'): {'query': {'categorymembers': [{'title': 'Category:Plenarsaal'}]}},
        ('commons.wikimedia.org', 'categorymembers', 'Category:Plenarsaalfile'): {'query': {'categorymembers': [{'title': 'File:Stuhl.jpg'}]}}})
    spec = os.path.join(tmp, 'spec.json'); urls.clear()
    json.dump([{'q': 'Gerichtssaal', 'want': "inside a courtroom with a judge's bench", 'keep': 3}, 'wiki: Bundestag', {'q': 7}, 'wiki: Merz'], open(spec, 'w'))
    sys.argv = ['find_images.py', o2, '--spec', spec]; os.environ['FIND_SEEN'] = o1
    F.main()
    idx = json.load(open(os.path.join(o2, 'index.json'), encoding='utf-8'))
    # ranked by the score, the search's order counting a little (A, first of the search, before F); C does not show
    # it, E is unsuitable, B05 fits but was shown in round 1; "keep" pictures are kept
    assert [(r['title'], r['match']) for r in idx[0]['results']] == [('File:GB.jpg', 0.33), ('File:GD.jpg', 0.30), ('File:GA.jpg', 0.285)], idx[0]
    assert idx[0]['want'] == "inside a courtroom with a judge's bench" and idx[0]['candidates'] == 7 and texts == [idx[0]['want']]
    assert '1 not showing what was asked, 1 unsuitable' in said.getvalue(), said.getvalue()[-300:]
    assert [a for a in urls if 'generator=search' in a and 'gsrlimit=30' in a] and sum('/330px-G' in a for a in urls) == 6
    # wiki: the item's own picture, then the articles' (German first), the category's and its sub-category's, then
    # the photos taken there (one of a series); page furniture and files that are not on Commons are left out
    assert [(r['title'], r['source']) for r in idx[1]['results']] == [('File:Reichstag.jpg', 'commons/wiki'), ('File:Plenarsaal.jpg', 'commons/wiki'),
        ('File:Kuppel.jpg', 'commons/wiki'), ('File:Sitzung.jpg', 'commons/category'), ('File:Stuhl.jpg', 'commons/category'), ('File:Wiese 001.jpg', 'commons/geo')], idx[1]
    assert idx[1]['wikidata'] == {'id': 'Q154797', 'label': 'Deutscher Bundestag', 'description': 'Parlament der Bundesrepublik Deutschland', 'coord': [52.5186, 13.3762]}
    assert 'match' not in idx[1]['results'][0] and idx[1]['query'] == 'wiki: Bundestag' and not any('svg' in a or 'logo' in a.lower() for a in urls)
    assert 'ValueError' in idx[2]['error'] and idx[2]['results'] == [] and 'no Wikidata item named "Merz"' in idx[3]['error'], idx[2:]
    assert sorted(f for f in os.listdir(o2) if f.startswith('sheet')) == ['sheet_1.jpg', 'sheet_2.jpg']
    # the pictures were found but none could be downloaded: an error (to search again), not "nothing found"
    LIB['kaputt'] = [_pg('File:Merz kaputt.jpg', 2000, 3000, i=1)]
    sys.argv = ['find_images.py', os.path.join(tmp, '3'), 'incategory:"Friedrich Merz"', 'kaputt']; os.environ['FIND_RANK'] = '0'; os.environ.pop('FIND_SEEN')
    F.Clip.ready = real_find[2]
    F.main()
    idx = json.load(open(os.path.join(tmp, '3', 'index.json'), encoding='utf-8'))
    assert len(idx[0]['results']) == 1 and 'error' not in idx[0] and 'none could be downloaded' in idx[1]['error'] and idx[1]['candidates'] == 1, idx
finally:
    F.get, F.picture, F.Clip.ready, F.Clip.scores, sys.argv = real_find[:5]
    for name, v in (('FIND_RANK', real_find[5]), ('FIND_SEEN', real_find[6])):
        os.environ.pop(name, None) if v is None else os.environ.__setitem__(name, v)
    F.FOUND.clear(); quiet.__exit__(None, None, None); shutil.rmtree(tmp, ignore_errors=True)
# run.py hands the queries over: plain strings on the command line as always, a list with a wish as a file
tmp = tempfile.mkdtemp(prefix='news-units-'); spec = os.path.join(tmp, 'out', 'find.json')
assert run.find_args(['incategory:"Friedrich Merz"', 'wiki: Bundestag'], spec) == ['incategory:"Friedrich Merz"', 'wiki: Bundestag'] and not os.path.exists(spec)
mixed = ['wiki: Bundestag', {'q': 'Gerichtssaal', 'want': 'inside a courtroom'}]
assert run.find_args(mixed, spec) == ['--spec', spec] and json.load(open(spec, encoding='utf-8')) == mixed
shutil.rmtree(tmp, ignore_errors=True)
# the runbook tells Claude every kind of query the search knows
runbook = open(os.path.join(ROOT, 'AGENT_NEWS.md'), encoding='utf-8').read()
assert all(w in runbook for w in ('wiki: Friedrich Merz', 'wiki: Bundestag', 'geo: ', '"want"', 'incategory:', '"wikidata"')), 'AGENT_NEWS.md: a query kind is not explained'
print('news unit checks OK')
