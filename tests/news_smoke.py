#!/usr/bin/env python3
"""Smoke test of the news pipeline on made-up data (no 11labs, no picture search, no network):
pictures → prep.py → build.py → fonts.py (when FONTSOURCE is set) → preview.py → sheet-independent checks, and with
--still one Remotion frame of the NewsV composition. Run from the repo root: python3 tests/news_smoke.py [--still]"""
import json, os, re, subprocess, sys, tempfile
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'news'))
import ff

N = '0'
tmp = tempfile.mkdtemp(prefix='news-smoke-')
job, pub, imgsrc, out = (os.path.join(tmp, d) for d in ('job', 'public', 'imgsrc', 'out'))
voice = os.path.join(pub, 'news', N, 'voice')
for d in (job, os.path.join(imgsrc, '1'), voice, out): os.makedirs(d)
run = lambda *a: subprocess.run(a, check=True, cwd=ROOT)

# pictures: a wide painting, a tall portrait, a small old photo
rng = np.random.RandomState(1)
for name, (w, h) in {'1-1.jpg': (1600, 1100), '1-2.jpg': (800, 1200), '1-3.jpg': (600, 450)}.items():
    yy, xx = np.mgrid[0:h, 0:w]
    a = np.stack([xx / w * 255, yy / h * 255, 128 + 60 * np.sin(xx / 40.0)], axis=2) + rng.normal(0, 8, (h, w, 3))
    Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(os.path.join(imgsrc, '1', name), quality=90)
json.dump([{'k': 1, 'query': 'test', 'results': [
    {'title': 'File:Wide.jpg', 'page': 'https://commons.wikimedia.org/wiki/File:Wide.jpg', 'license': 'Public domain', 'artist': 'A', 'date': '1850', 'file': '1-1.jpg'},
    {'title': 'File:Tall.jpg', 'page': 'https://commons.wikimedia.org/wiki/File:Tall.jpg', 'license': 'CC BY 4.0', 'artist': 'B', 'date': '1900', 'file': '1-2.jpg'},
    {'title': 'File:Small.jpg', 'page': 'https://commons.wikimedia.org/wiki/File:Small.jpg', 'license': 'CC0', 'artist': 'C', 'date': '', 'file': '1-3.jpg'}]}],
    open(os.path.join(imgsrc, '1', 'index.json'), 'w'))

# voice: silent lines of known length
lines = ['Der Bundestag hat heute ein neues Gesetz beschlossen.', 'Was ändert sich jetzt für Sie?',
         'Ab Januar steigt der Mindestlohn auf vierzehn Euro, und rund sechs Millionen Beschäftigte bekommen dadurch mehr Geld.', 'Die Opposition übt Kritik.']
durs = [3.4, 1.8, 7.6, 1.5]; rows = []
for i, (t, d) in enumerate(zip(lines, durs), 1):
    f = f'line_{i:02d}.mp3'
    ff.run('-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=mono', '-t', str(d), '-c:a', 'libmp3lame', '-q:a', '5', os.path.join(voice, f))
    rows.append({'i': i, 'text': t, 'tts': t, 'voice': 'test', 'file': f, 'duration': round(ff.duration(os.path.join(voice, f)), 3)})
json.dump(rows, open(os.path.join(voice, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False)

cam = lambda z0, z1: {'from': {'z': z0, 'x': .5, 'y': .5}, 'to': {'z': z1, 'x': .45, 'y': .4}}
json.dump({'title': 'Test', 'voice': 'test', 'lines': lines, 'show_chapters': '--chapters' in sys.argv,
           'head': {'title': 'Mindestlohn steigt auf vierzehn Euro', 'sub': 'Berlin, Bundestag'}, 'quotes': [4],
           'chapters': [{'num': '01', 'label': 'Berlin', 'title': 'Neues Gesetz', 'desc': ['Erste Zeile', 'Zweite Zeile'], 'lines': [1, 2]},
                        {'num': '02', 'label': 'Folgen', 'title': 'Mehr Geld', 'desc': ['Erste Zeile', 'Zweite Zeile'], 'lines': [3, 4]}],
           'hl': {'1': ['Gesetz'], '3': ['Mindestlohn']}, 'ambience': ['', 'wind'], 'queries': ['test']},
          open(os.path.join(job, 'script.json'), 'w', encoding='utf-8'), ensure_ascii=False)
json.dump({'images': {'wide': {'src': '1/1-1.jpg', 'mode': 'color'}, 'tall': {'src': '1/1-2.jpg', 'mode': 'sepia'},
                      'small': {'src': '1/1-3.jpg', 'crop': [0.1, 0.1, 0.9, 0.9], 'mode': 'keep'}},
           'chapters': [{'pics': [{'img': 'wide', **cam(1.0, 1.2), 'credit': 'Foto: A / Wikimedia Commons, CC BY-SA 4.0', 'tag': 'Berlin'},
                                  {'at': 2, 'pair': {'left': {'img': 'tall', 'caption': ['Vorname Name', 'Bundeskanzler']}, 'right': {'img': 'small'}}, 'credit': 'Links: Porträt · Rechts: Dokument'}]},
                        {'pics': [{'img': 'small', **cam(1.1, 1.0), 'credit': 'Archivbild'}, {'at': 3.5, 'img': 'tall', **cam(1.0, 1.4), 'credit': 'Symbolbild'}]}]},
          open(os.path.join(job, 'picks.json'), 'w', encoding='utf-8'), ensure_ascii=False)

S = os.path.join(ROOT, 'scripts', 'news')
run(sys.executable, os.path.join(S, 'prep.py'), os.path.join(job, 'picks.json'), imgsrc, os.path.join(pub, 'news', N, 'img'))
run(sys.executable, os.path.join(S, 'build.py'), job, pub, N, imgsrc, out)
plan_p = os.path.join(out, 'plan.json')
if os.environ.get('FONTSOURCE'):
    run(sys.executable, os.path.join(S, 'fonts.py'), plan_p, os.environ['FONTSOURCE'], pub)
run(sys.executable, os.path.join(S, 'preview.py'), os.path.join(job, 'picks.json'), os.path.join(job, 'script.json'), imgsrc, os.path.join(out, 'preview.jpg'))

plan = json.load(open(plan_p, encoding='utf-8'))
speech = sum(r['duration'] for r in rows)
assert speech + 3 < plan['duration'] < speech + 9, plan['duration']            # pauses and chapter breaths only
assert [len(c['pics']) for c in plan['chapters']] == [2, 2]
assert plan['chapters'][0]['pics'][1]['pair']['left']['w'] > 0
for c in plan['chapters']:                                                       # pictures tile the chapter without gaps
    assert c['pics'][0]['s'] == c['s'] and c['pics'][-1]['e'] == c['e'] and all(a['e'] == b['s'] for a, b in zip(c['pics'], c['pics'][1:]))
mid = plan['chapters'][1]['pics'][1]['s']; v3 = plan['voice'][2]['s']
assert v3 + 1.5 < mid < v3 + rows[2]['duration'], (mid, v3)                     # at 3.5 = halfway through line 3
assert len(plan['voice']) == 4 and all(a['s'] < b['s'] for a, b in zip(plan['voice'], plan['voice'][1:]))
for sb in plan['subs']:                                                          # at most two rows, readable size
    r = sb['text'].split('\n'); assert len(r) <= 2 and max(map(len, r)) <= 38, sb['text']
assert len(plan['subs']) == 5, [s['text'] for s in plan['subs']]                 # the long line 3 becomes two cues
assert [bool(s.get('box')) for s in plan['subs']] == [False] * 4 + [True]        # line 4 is a quote
assert plan['head']['title'] == 'Mindestlohn steigt\nauf vierzehn Euro', plan['head']
assert plan['head']['cover']['src'].endswith('/wide.jpg') and len(plan['intro']) == 2   # cover = first picture, strip = the others
assert ' '.join(s['text'].replace('\n', ' ') for s in plan['subs']) == ' '.join(lines)
assert all(a['e'] <= b['s'] + 1e-6 for a, b in zip(plan['subs'], plan['subs'][1:]))
srt = open(os.path.join(out, 'subtitles.srt'), encoding='utf-8').read(); assert srt.count('-->') == 5
cue_t = [[sum(float(x) * k for x, k in zip(re.split('[:,]', v), (3600, 60, 1, .001))) for v in m] for m in re.findall(r'(\S+) --> (\S+)', srt)]
assert all(a[0] < a[1] <= b[0] + 1e-6 for a, b in zip(cue_t, cue_t[1:])), cue_t      # .srt cues never overlap
cred = open(os.path.join(out, 'credits.txt'), encoding='utf-8').read()
assert 'Wide.jpg' in cred and 'CC BY 4.0' in cred and 'commons.wikimedia.org' in cred
assert os.path.getsize(os.path.join(pub, 'news', N, 'bed.wav')) > 100000
assert Image.open(os.path.join(out, 'preview.jpg')).size[0] > 400
if os.environ.get('FONTSOURCE'):
    plan = json.load(open(plan_p, encoding='utf-8')); assert len(plan['fonts']) >= 2 and all(os.path.exists(os.path.join(pub, f['file'])) for f in plan['fonts'])

if '--still' in sys.argv:   # half-size frames: during the opening (1.5 s) and after it (5 s)
    run('node', os.path.join(S, 'stills.mjs'), plan_p, pub, os.path.join(out, 'still'), '1.5', '5')
    a = np.asarray(Image.open(os.path.join(out, 'still_1.5.png')).convert('RGB')).astype(int)
    b = np.asarray(Image.open(os.path.join(out, 'still_5.png')).convert('RGB')).astype(int)
    assert a.shape[:2] == b.shape[:2] == (960, 540), (a.shape, b.shape)
    assert a[360:510].std() > 20, 'no strip of pictures in the opening'
    assert b[270:625, 30:510].std() > 20, 'picture panel is flat'               # the picture is there
    assert (b[95:230, 160:520] > 200).mean() > 0.01, 'no headline'               # white headline beside the cover
    assert (b[655:760] > 200).mean() > 0.005, 'no subtitle text'                 # white subtitle text below the panel
print('news smoke test OK:', round(plan['duration'], 1), 's,', len(plan['subs']), 'cues,', tmp)
