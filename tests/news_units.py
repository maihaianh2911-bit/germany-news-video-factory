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
print('news unit checks OK')
