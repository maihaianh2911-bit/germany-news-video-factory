#!/usr/bin/env python3
"""Unit checks without network, Whisper or 11labs: the voice check's word comparison (numbers written out on both
sides), the whole-word readings sent to the voice, and the call to the Claude task (fresh news-busy label, comment
wording, retries). Run from the repo root:
python3 tests/news_units.py   (needs num2words: pip install num2words==0.5.14)"""
import contextlib, datetime, io, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'news'))
from voice_check import compare
from tts_lines import spoken

flagged = lambda sent, heard: compare(sent, heard)[1]

# a wrong number is a misreading; the same number written in digits or in words is not
assert flagged('Die Inflation liegt bei 3,5 Prozent.', 'Die Inflation liegt bei drei fünf Prozent.'), 'wrong decimal not flagged'
assert not flagged('Die Inflation liegt bei 3,5 Prozent.', 'Die Inflation liegt bei drei Komma fünf Prozent.')
assert not flagged('Die Inflation liegt bei 3,5 %.', 'Die Inflation liegt bei 3,5 Prozent.')
assert flagged('Der Mindestlohn steigt auf 14 Euro.', 'Der Mindestlohn steigt auf vier Euro.')
assert not flagged('Am 12. November kamen 1.000 Menschen.', 'Am zwölften November kamen tausend Menschen.')
assert not flagged('Am 1. Januar stieg er um 1 Prozent.', 'Am ersten Januar stieg er um ein Prozent.')
assert not flagged('Seit 1990 gilt § 5.', 'Seit neunzehnhundertneunzig gilt Paragraf fünf.')
assert not flagged('Er kam 2019. Dann ging er.', 'Er kam zweitausendneunzehn. Dann ging er.')
# short words must match exactly, long ones may differ only by spelling
assert flagged('Das ist ein Problem.', 'Das ist kein Problem.')
assert flagged('Das Bundesverfassungsgericht urteilt.', 'Das Bundesverwaltungsgericht urteilt.')
assert not flagged('Der Fluss ist breit.', 'Der Fluß ist breit.')

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
good = ("Fall Fabian: 44 Indizien – wird das Urteil gekippt?\n"
        "Das Landgericht Rostock verurteilte Gina H. zu lebenslanger Haft. Sie beteuert ihre Unschuld.\n"
        "Jetzt prüft der Bundesgerichtshof die Revision.\n\n"
        "#Nachrichten #FallFabian #TrueCrime #Rostock #Bundesgerichtshof #shorts\n\n"
        "Bildquellen: Bernd Wüstneck/dpa; Wikimedia Commons (siehe credits)\n")
assert caption.check(good) == [], caption.check(good)
assert caption.check(good.replace('Fall Fabian: 44', 'Fall Fabian: ' + 'x' * 80))[0].startswith('tiêu đề dài')
assert any('hashtag' in b for b in caption.check(good.replace(' #Rostock #Bundesgerichtshof #shorts', '')))   # 3 tags
assert any('Bildquellen' in b for b in caption.check(good.replace('Bildquellen:', 'Fotos:')))
assert any('tiếng Đức' in b for b in caption.check(good.replace('Jetzt prüft', 'Tòa án Tối cao sẽ xét lại')))      # Vietnamese
assert any('tiếng Đức' in b for b in caption.check(good.replace('Jetzt prüft', '連邦裁判所が')))                # Japanese
assert any('mô tả' in b for b in caption.check(good.split('\n')[0] + '\n\n#a #b #c #d #e\n\nBildquellen: x'))
assert any('2000' in b for b in caption.check(good.replace('Jetzt prüft', 'Satz. ' * 400 + 'Jetzt prüft')))
assert caption.check('') == ['caption.txt trống'] and len(caption.check('Nur ein Titel')) == 1
print('news unit checks OK')
