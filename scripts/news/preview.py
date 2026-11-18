#!/usr/bin/env python3
"""Preview every shot of picks.json before rendering: the full frame (1080×1920) at the start and at the end of
its camera move, exactly as NewsV frames it, in one contact sheet; the yellow box marks where the subtitles sit.
Catches cut-off faces, faces under the subtitles and wrong framing before a render.
Usage: preview.py <news/N/picks.json> <news/N/script.json> <img_root> <out.jpg>
(<img_root> = the renders folder news/<N>/img with rounds 1/, 2/…, plus own/ when used).
Each tile is labelled with the shot's move (moves.py; "-" = hand-written numbers). Next to the sheet it writes
<out>.md, the list of edits for the owner (shot, line, picture, move, why), and prints it. Shot lengths come from
the measured voice (<img_root>/../voice/lines.json) when it is there, else from an estimate of the reading speed.
An unknown move or a shot without a move stops here with the list of valid names. A shot too short for its move
or a "wide" point that would lose the subject is printed as WARNING and its tile is marked "!".
A "Top X" video (picks.json "top") also gets <out>_top.jpg: the hook of line 1 (title and round portraits) next to
line 2's "PLATZ <rank>" over its picture, half size, to check that every face sits well in its circle."""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from prep import prepare
import moves

picks_p, script_p, root, out = sys.argv[1:5]
picks = json.load(open(picks_p, encoding='utf-8')); script = json.load(open(script_p, encoding='utf-8'))
bad = moves.check_all(picks)
if bad: sys.exit('picks.json: ' + '; '.join(bad))
vl = os.path.join(root, '..', 'voice', 'lines.json'); dur = None
if os.path.exists(vl):
    rows = json.load(open(vl, encoding='utf-8')); dur = {r['i']: r['duration'] for r in rows}; text = {r['i']: r['text'] for r in rows}
    if len(dur) != len(script['lines']): dur = None   # the script changed since that voice: estimate instead
if dur is None:
    dur = moves.estimate(script['lines']); text = dict(enumerate(script['lines'], 1))
pace = float(script.get('pace', 1.0))   # the voice is sped up by this factor at the render (build.py)
dur = {i: d / pace for i, d in dur.items()}
times = moves.shot_times(script['chapters'], picks['chapters'], dur, text, pace)
W, PH, TW, TH = 1080, 1920, 162, 288
cache = {}
def img(name):
    if name not in cache: cache[name] = prepare(picks['images'][name], root)
    return cache[name]

def window(im, cam):
    """The frame of NewsV's PicView: cover-fit × z, point (x, y) at the centre, clamped to the picture."""
    w, h = im.size; c = max(W / w, PH / h) * cam['z']; dw, dh = w * c, h * c
    left = min(0, max(W - dw, W / 2 - cam['x'] * dw)); top = min(0, max(PH - dh, PH / 2 - cam['y'] * dh))
    box = (-left / c, -top / c, (-left + W) / c, (-top + PH) / c)
    return im.crop(tuple(round(v) for v in box)).resize((TW, TH), Image.LANCZOS)

def subtitle_band(tile):
    """Outline of the subtitle area (NewsV: two rows centred at y = 1496)."""
    k = TH / PH; ImageDraw.Draw(tile).rectangle((round(150 * k), round(1420 * k), round(930 * k), round(1572 * k)), outline=(238, 197, 20))
    return tile

tiles = []; warn = []
for ci, (c, pc) in enumerate(zip(script['chapters'], picks['chapters'])):
    a, b = c['lines']; n = len(pc['pics'])
    for j, p in enumerate(pc['pics']):
        line = a if j == 0 else (p.get('at') or a + round(j * (b - a + 1) / n))
        name = p['img']; s, e, _ = times[ci][j]
        c0, c1 = moves.camera(p, *img(name).size, e - s)
        for wmsg in moves.warnings(p, *img(name).size, e - s): warn.append(f'shot {ci + 1}-{j + 1} ({name}): {wmsg}')
        t0, t1 = subtitle_band(window(img(name), c0)), subtitle_band(window(img(name), c1))
        tile = Image.new('RGB', (TW * 2 + 6, TH + 22), (12, 12, 14))
        tile.paste(t0, (0, 22)); tile.paste(t1, (TW + 6, 22))
        mark = ' !' if warn and warn[-1].startswith(f'shot {ci + 1}-{j + 1} ') else ''
        ImageDraw.Draw(tile).text((4, 5), f'{ci + 1}-{j + 1} l.{line} {name} [{moves.label(p)}]{mark}'[:52], fill=(255, 210, 90))
        tiles.append(tile)
def font(size):
    """A font with German letters for the sheet (NewsV draws with Philosopher)."""
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)

def boxes(dr, rows, size, y):
    """Yellow boxes with dark text centred at y, as NewsV's Boxes (approximate font)."""
    f = font(size); hh = size * 1.18 + 16; yy = y - hh * len(rows) / 2
    for r in rows:
        w = dr.textlength(r, font=f)
        dr.rounded_rectangle((540 - w / 2 - 22, yy, 540 + w / 2 + 22, yy + hh), 14, fill=(238, 197, 20))
        dr.text((540 - w / 2, yy + 6), r, font=f, fill=(30, 16, 6)); yy += hh - 8

top = picks.get('top')
if top:   # the shared hook, laid out as NewsV's TopGrid (the numbers are kept equal by hand)
    first = picks['chapters'][0]['pics'][0]
    g = window(img(first['img']), moves.camera(first, *img(first['img']).size, 3)[0]).resize((W, PH)).point(lambda v: v * 0.2)
    dr = ImageDraw.Draw(g); ppl = top['people']; n = len(ppl); per = 2 if n == 4 else 3
    rws = [ppl[k:k + per] for k in range(0, n, per)]; gap = 70; m = min(per, n); d = min(340, (1000 - (m - 1) * gap) // m)
    rowH = d + 120; y0 = 1020 - (len(rws) - 1) * rowH / 2
    boxes(dr, moves.title_rows(top['title']), 64 if max(map(len, moves.title_rows(top['title']))) > 22 else 76, 330)
    k = 0
    for ri, row in enumerate(rws):
        for j, pp in enumerate(row):
            cx, cy = 540 + (j - (len(row) - 1) / 2) * (d + gap), y0 + ri * rowH
            im = img(pp['img']); left, tp, c = moves.circle_window(*im.size, d, pp.get('focus'), max(1, pp.get('zoom', 1.0)))
            crop = im.crop((round(-left / c), round(-tp / c), round((-left + d) / c), round((-tp + d) / c))).resize((d, d))
            mask = Image.new('L', (d, d), 0); ImageDraw.Draw(mask).ellipse((0, 0, d - 1, d - 1), fill=255)
            g.paste(crop, (round(cx - d / 2), round(cy - d / 2)), mask)
            me = k == top['me']; k += 1
            dr.ellipse((cx - d / 2 - 5, cy - d / 2 - 5, cx + d / 2 + 5, cy + d / 2 + 5), outline=(238, 197, 20) if me else (244, 236, 216), width=10 if me else 5)
            f = font(40); w = dr.textlength(pp['name'], font=f)
            dr.text((cx - w / 2, cy + d / 2 + 22), pp['name'], font=f, fill=(255, 255, 255))
    second = next((p for c in picks['chapters'] for p in c['pics'] if p.get('at') == 2), None)
    b = window(img(second['img']), moves.camera(second, *img(second['img']).size, 3)[0]).resize((W, PH)) if second else Image.new('RGB', (W, PH))
    boxes(ImageDraw.Draw(b), [f"PLATZ {top['rank']}"], 130, 300)
    ts = Image.new('RGB', (W + 20, PH // 2), (0, 0, 0)); ts.paste(g.resize((W // 2, PH // 2)), (0, 0)); ts.paste(b.resize((W // 2, PH // 2)), (W // 2 + 20, 0))
    top_out = os.path.splitext(out)[0] + '_top.jpg'; ts.save(top_out, quality=85); print('top hook:', top_out)
    if not second: warn.append('top: no shot starts at line 2 ("at": 2), so "PLATZ …" is not over this writer')
cols = 4; rows = (len(tiles) + cols - 1) // cols; tw, th = tiles[0].size
sheet = Image.new('RGB', (cols * (tw + 10), rows * (th + 8)), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (tw + 10), (i // cols) * (th + 8)))
sheet.save(out, quality=82)
md = os.path.splitext(out)[0] + '.md'
open(md, 'w', encoding='utf-8').write(moves.edits_md(script['chapters'], picks, times, text))
# the picture review (owner, 18/11/2026, from the Japanese channel: "đọc lại hình ảnh đã chọn xem đã phù hợp với nội
# dung cần thể hiện chưa, chưa thì chọn lại, duyệt lại, khi nào ổn mới lấy"): every shot beside all the words spoken
# while it is on screen and the title of the picture where it was found
titles = {}
for rnd in sorted(os.listdir(root)) if os.path.isdir(root) else []:
    ip = os.path.join(root, rnd, 'index.json')
    if os.path.exists(ip):
        for q in json.load(open(ip, encoding='utf-8')):
            for r in q.get('results', []):
                if r.get('file'): titles[f"{rnd}/{r['file']}"] = r.get('title', '').replace('File:', '')
rows, n = [], 0
for ci, (c, pc) in enumerate(zip(script['chapters'], picks['chapters'])):
    a, b = c['lines']
    for j, p in enumerate(pc['pics']):
        n += 1; s, e, li = times[ci][j]
        nxt = pc['pics'][j + 1].get('at') if j + 1 < len(pc['pics']) else None
        last = b if j + 1 == len(pc['pics']) else times[ci][j + 1][2] - (0 if nxt and nxt != int(nxt) else 1)   # a cut inside a line shares it
        words = ' '.join(' '.join(text.get(i, '').split()) for i in range(li, last + 1))
        src = picks['images'][p['img']]['src']
        rows.append(f"{n}. {int(s // 60)}:{int(s % 60):02d}–{int(e // 60)}:{int(e % 60):02d} {p['img']} ({titles.get(src, src)})\n   {words}")
open(os.path.splitext(out)[0] + '_review.md', 'w', encoding='utf-8').write(
    'Duyệt ảnh: mỗi ảnh cạnh lời đọc lúc nó trên hình. Đúng người, nơi, sự việc, thời kỳ; mặt không bị cắt; '
    'ảnh sạch, đủ nét; không trùng ảnh khác.\n\n' + '\n'.join(rows) + '\n')
print(open(md, encoding='utf-8').read())
for wmsg in warn: print('WARNING:', wmsg)
print(out, len(tiles), 'shots', sheet.size, '| edits:', md, f'| {len(warn)} warning(s): fix them, their tiles are marked "!"' if warn else '')
