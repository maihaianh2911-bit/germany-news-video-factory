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
print('news unit checks OK')
