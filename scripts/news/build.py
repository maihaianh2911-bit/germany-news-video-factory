#!/usr/bin/env python3
"""Plan of a news video for the NewsV composition, plus music bed, subtitles and picture credits.

Usage: build.py <job_dir news/N> <public_dir> <N> <img_src_dir> <out_dir>
Reads <job_dir>/script.json (lines, chapters, head, quotes, ambience, music), <job_dir>/picks.json (pictures per
chapter, cover), <public_dir>/news/<N>/voice/lines.json (measured line lengths), the prepared pictures in
<public_dir>/news/<N>/img/ and the channel name in prompts/news_style.json. Writes <out_dir>/plan.json,
subtitles.srt, credits.txt and <public_dir>/news/<N>/bed.wav.
Timing: every line starts after the previous one plus a pause (0.45 s after a sentence end, 0.25 s otherwise);
each chapter opens with a short breath; a picture that starts on a line ("at") cuts in just before it is spoken.
Credits: a search result is listed from its round's index.json (title, author, date, licence, File: page); any other
picture (own/…) by its on-screen credit, plus the optional picks.json image key "page" (source URL) on the next line.
"""
import json, os, re, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import music_gen as mg

job, pub, N, imgsrc, out = sys.argv[1:6]
base = f'news/{N}'
spec = json.load(open(f'{job}/script.json', encoding='utf-8'))
picks = json.load(open(f'{job}/picks.json', encoding='utf-8'))
lines = json.load(open(f'{pub}/{base}/voice/lines.json', encoding='utf-8'))
style_p = os.path.join(HERE, '..', '..', 'prompts', 'news_style.json')
style = json.load(open(style_p, encoding='utf-8')) if os.path.exists(style_p) else {}
dur = {r['i']: r['duration'] for r in lines}
text = {r['i']: r['text'] for r in lines}
os.makedirs(out, exist_ok=True)

# ---- subtitles: a spoken line becomes one cue of up to two rows, or several cues when it is too long.
# Rows break between words, best after a comma, colon or dash, never leaving a short word alone.
ROW = 34   # characters per row at full size (47 px, Source Serif 4)
END = ('.', '!', '?', '…', '“', '"', '«', '»')
MIN_PIECE = 8   # no break that leaves a piece this short ("Die" alone before a long compound)
def breaks(t):
    """Possible break points (index of the space, penalty): 0 after punctuation, 3 between plain words."""
    return [(k, 0 if t[k - 1] in ',;:–—' else 3) for k in range(1, len(t) - 1)
            if t[k] == ' ' and k >= MIN_PIECE and len(t) - k - 1 >= MIN_PIECE]
def two_rows(t):
    bs = breaks(t)
    if not bs: return [t]
    k = min(bs, key=lambda b: max(b[0], len(t) - b[0] - 1) + b[1])[0]
    return [t[:k], t[k + 1:]]
def cues(t):
    t = t.strip()
    if len(t) <= ROW: return [[t]]
    r = two_rows(t)
    if max(map(len, r)) <= ROW + 4 or len(r) == 1: return [r]   # up to 4 over: the font shrinks a little
    bs = breaks(t); cand = [b for b in bs if b[1] == 0 and 12 <= b[0] <= len(t) - 12] or bs
    k = min(cand, key=lambda b: abs(b[0] - len(t) / 2))[0]
    return cues(t[:k]) + cues(t[k + 1:])

# a quote (a whole line in quotation marks, or listed in script.json "quotes") is shown in a white box
OPEN, CLOSE = '„"«»‚\'', '“"»«‘\''
quotes = {int(q) for q in spec.get('quotes', [])}
is_quote = lambda i: i in quotes or (len(text[i].strip()) > 2 and text[i].strip()[0] in OPEN and text[i].strip()[-1] in CLOSE)

# ---- timeline
t = 0.0; chapters = []; subs = []; voice = []
img = lambda name: f'{base}/img/{name}.jpg'
for ci, c in enumerate(spec['chapters']):
    a, b = c['lines']; s = t; x = s + (1.0 if ci == 0 else 0.8); starts = []
    for i in range(a, b + 1):
        voice.append({'s': round(x, 3), 'src': f'{base}/voice/{lines[i - 1]["file"]}'})
        parts = cues(text[i]); n_all = len(text[i].strip()) + 1
        if len(parts) > 1 and min(len(' '.join(cu)) for cu in parts) / n_all * dur[i] < 1.0 and max(map(len, two_rows(text[i].strip()))) <= ROW + 8: parts = [two_rows(text[i].strip())]
        done = 0
        for cu in parts:   # cues share the line's time in proportion to their length
            cs = x + dur[i] * done / n_all; done += len(' '.join(cu)) + 1; ce = x + dur[i] * done / n_all
            subs.append({'s': round(cs, 3), 'e': round(ce - (0.12 if done < n_all else 0), 3), 'text': '\n'.join(cu), **({'box': True} if is_quote(i) else {})})
        starts.append(x)
        x += dur[i] + (0.45 if text[i].rstrip().endswith(END) else 0.25)
    e = x + (2.6 if ci == len(spec['chapters']) - 1 else 0.7)
    ch = {'s': round(s, 3), 'e': round(e, 3), **{q: c[q] for q in ('num', 'label', 'title', 'desc')}, 'pics': []}
    pics = picks['chapters'][ci]['pics']; n = len(pics)
    bounds = [s]
    for j in range(1, n):
        li = pics[j].get('at') or a + round(j * (b - a + 1) / n)
        k = min(len(starts) - 1, max(0, int(li) - a))
        bounds.append(starts[k] + (li - int(li)) * dur[a + k] - 0.15)
    bounds.append(e)
    for j, p in enumerate(pics):
        q = {k: v for k, v in p.items() if k not in ('at', 'img')}
        if 'pair' in p:   # portrait + document as framed prints
            for side in ('left', 'right'):
                sd = dict(p['pair'][side]); sd['src'] = img(sd.pop('img'))
                sd['w'], sd['h'] = Image.open(f"{pub}/{sd['src']}").size; q['pair'] = {**q.get('pair', {}), side: sd}
            q.update({'src': '', 'w': 1, 'h': 1, 'from': {'z': 1, 'x': .5, 'y': .5}, 'to': {'z': 1, 'x': .5, 'y': .5}})
        else:
            q['src'] = img(p['img']); q['w'], q['h'] = Image.open(f"{pub}/{q['src']}").size
        ch['pics'].append({**q, 's': round(bounds[j], 3), 'e': round(bounds[j + 1], 3)})
    chapters.append(ch); t = e
total = round(t, 3)

# ---- music bed: a quiet score made for this length, plus nature sounds under the chapters that ask for them
mu = {'style': 'documentary', 'key': 'A', 'mode': 'minor', 'bpm': 62, 'energy': 0.3, **spec.get('music', {})}
SR = mg.SR
music = mg.render([{'from': 0, 'to': total, **mu}], lambda v: v, total)
n = len(music); rng = np.random.RandomState(9); tt = np.arange(n) / SR
def env(a, b, fade=1.0):
    e = np.zeros(n); i0, i1 = int(a * SR), min(n, int(b * SR)); k = int(fade * SR)
    e[i0:i1] = 1; e[i0:i0 + k] = np.linspace(0, 1, k); e[i1 - k:i1] = np.linspace(1, 0, k); return e
nz = lambda v: v / (np.abs(v).max() or 1)
amb = np.zeros(n)
for ci, kind in enumerate(spec.get('ambience', [])):
    if ci >= len(chapters) or not kind: continue
    c = chapters[ci]; w = env(c['s'], c['e'])
    if kind == 'water': amb += 0.6 * nz(mg.hp(mg.lp(rng.normal(0, 1, n), 2500), 300)) * w
    elif kind == 'wind': amb += 0.7 * nz(mg.lp(rng.normal(0, 1, n), 300) * (0.6 + 0.4 * np.sin(tt * 0.6))) * w
    elif kind == 'rain': amb += 0.55 * nz(mg.hp(mg.lp(rng.normal(0, 1, n), 7000), 900)) * w
    elif kind == 'sea': amb += 0.9 * nz(mg.lp(rng.normal(0, 1, n), 600) * (0.45 + 0.55 * np.clip(np.sin(tt * 2 * np.pi / 6.5), 0, 1) ** 2)) * w
bed = 0.75 * music + 0.3 * amb; bed = bed / (np.abs(bed).max() or 1) * 0.8
mg.write_wav(f'{pub}/{base}/bed.wav', bed)

# ---- header (cover picture, headline, italic line, channel) and the opening strip of pictures
def head_rows(title):
    """The headline as written when it has its own row break, else in one row, or two rows broken at the space
    that keeps the longer row shortest."""
    if '\n' in title: return title.strip()
    title = ' '.join(title.split())
    if len(title) <= 20: return title
    ks = [k for k, ch_ in enumerate(title) if ch_ == ' ']
    if not ks: return title
    k = min(ks, key=lambda k: max(k, len(title) - k - 1) - (2 if title[k - 1] in ':,–—' else 0))
    return title[:k] + '\n' + title[k + 1:]
order = []   # picture names in order of appearance, with the camera point of their first use
for pc in picks['chapters']:
    for p in pc['pics']:
        if 'img' in p and p['img'] not in dict(order): order.append((p['img'], p['from']))
def thumb(name, x=None, y=None):
    cam = dict(order).get(name, {'x': .5, 'y': .4})
    src = img(name); w, h = Image.open(f'{pub}/{src}').size
    return {'src': src, 'w': w, 'h': h, 'x': x if x is not None else cam['x'], 'y': y if y is not None else cam['y']}
cv = picks.get('cover') or ({'img': order[0][0]} if order else None)
cover = thumb(cv['img'], cv.get('x'), cv.get('y')) if cv else None
hd = spec.get('head', {})
head = {'title': head_rows(hd.get('title') or spec.get('title', '')), 'sub': hd.get('sub', ''),
        'channel': style.get('channel', ''), 'cover': cover}
strip = [thumb(n) for n, _ in order if not cv or n != cv['img']][:10] or ([cover] if cover else [])
plan = {'duration': total, 'showChapters': spec.get('show_chapters', False), 'head': head,
        'intro': strip if spec.get('intro', True) and cover else [],
        'chapters': chapters, 'subs': subs, 'voice': voice, 'music': f'{base}/bed.wav', 'musicVolume': 0.3,
        'fonts': []}
json.dump(plan, open(f'{out}/plan.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

def ts(v):
    ms = int(round(v * 1000)); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s_, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s_:02d},{ms:03d}'
def srt_end(k):
    """End of cue k (0-based): held 0.2 s longer for reading, but never past the start of the next cue."""
    e = subs[k]['e'] + 0.2
    return min(e, subs[k + 1]['s']) if k + 1 < len(subs) else e
with open(f'{out}/subtitles.srt', 'w', encoding='utf-8') as f:
    for k, sb in enumerate(subs): f.write(f"{k + 1}\n{ts(sb['s'])} --> {ts(srt_end(k))}\n{sb['text']}\n\n")

# ---- credits for the video description (every picture: title, author, date, licence, page)
idx = {}
for rnd in sorted(os.listdir(imgsrc)) if os.path.isdir(imgsrc) else []:
    ip = os.path.join(imgsrc, rnd, 'index.json')
    if os.path.exists(ip):
        for q in json.load(open(ip, encoding='utf-8')):
            for r in q['results']:
                if r.get('file'): idx[f"{rnd}/{r['file']}"] = r
said = {}   # the on-screen credit of each picture (photographer and agency for press photos in own/)
for ch in picks['chapters']:
    for pic in ch['pics']:
        for part in [pic] + [pic['pair'][side] for side in ('left', 'right') if 'pair' in pic]:
            if part.get('img') and part.get('credit'): said.setdefault(part['img'], part['credit'])
        if 'pair' in pic and pic.get('credit'):
            for side in ('left', 'right'): said.setdefault(pic['pair'][side].get('img'), pic['credit'])
seen, rows = set(), []
for name, it in picks['images'].items():
    r = idx.get(it['src'])
    if not r:
        text = said.get(name) or (f"{it['src']} (ảnh chủ kênh gửi)" if it['src'].startswith('own/') else it['src'])
        if text in seen: continue
        seen.add(text)
        rows.append(f"- {text}" + (f"\n  {it['page']}" if it.get('page') else '')); continue
    if r['page'] in seen: continue
    seen.add(r['page'])
    date = re.sub(r'date QS.*', '', r.get('date') or '').strip()
    artist = re.sub(r'\s+', ' ', r.get('artist') or '').strip()
    rows.append(f"- {r['title'][5:]} — {artist}{f' ({date})' if date else ''} — {r['license']}\n  {r['page']}")
open(f'{out}/credits.txt', 'w', encoding='utf-8').write(
    'Nguồn ảnh (ảnh báo chí ghi tên tác giả và hãng; ảnh Wikimedia Commons phạm vi công cộng / CC0 / CC BY / CC BY-SA — ảnh CC BY và CC BY-SA phải ghi tên tác giả và giấy phép trong mô tả video):\n\n'
    + '\n'.join(rows) + '\n')
print(f'total {total} s; ' + ', '.join(f"{c['num']}:{c['s']}–{c['e']} ({len(c['pics'])} ảnh)" for c in chapters))
