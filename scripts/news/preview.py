#!/usr/bin/env python3
"""Preview every shot of picks.json before rendering: the picture panel (1080×1000) at the start and at the end of
its camera move, exactly as NewsV frames it, in one contact sheet. Catches cut-off faces and wrong framing before
a 25-minute render. Usage: preview.py <news/N/picks.json> <news/N/script.json> <img_root> <out.jpg>
(<img_root> = the renders folder news/<N>/img with rounds 1/, 2/…, plus own/ when used)."""
import json, os, sys
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from prep import prepare

picks_p, script_p, root, out = sys.argv[1:5]
picks = json.load(open(picks_p, encoding='utf-8')); script = json.load(open(script_p, encoding='utf-8'))
W, PH, TW, TH = 1080, 1000, 216, 200
cache = {}
def img(name):
    if name not in cache: cache[name] = prepare(picks['images'][name], root)
    return cache[name]

def window(im, cam):
    """The panel view of NewsV's PicView: cover-fit × z, point (x, y) at the centre, clamped to the picture."""
    w, h = im.size; c = max(W / w, PH / h) * cam['z']; dw, dh = w * c, h * c
    left = min(0, max(W - dw, W / 2 - cam['x'] * dw)); top = min(0, max(PH - dh, PH / 2 - cam['y'] * dh))
    box = (-left / c, -top / c, (-left + W) / c, (-top + PH) / c)
    return im.crop(tuple(round(v) for v in box)).resize((TW, TH), Image.LANCZOS)

def pair_tile(p):
    t = Image.new('RGB', (TW, TH), (24, 20, 14)); k = TW / W
    for side, bw, x, y in (('left', 400, 70, 150), ('right', 440, 560, 110)):
        im = img(p['pair'][side]['img']); bh = bw * im.height / im.width
        th = im.resize((max(1, round(bw * k)), max(1, round(bh * k))))
        t.paste(th, (round(x * k), round(y * k)))
    return t

tiles = []
for ci, (c, pc) in enumerate(zip(script['chapters'], picks['chapters'])):
    a, b = c['lines']; n = len(pc['pics'])
    for j, p in enumerate(pc['pics']):
        line = a if j == 0 else (p.get('at') or a + round(j * (b - a + 1) / n))
        if 'pair' in p:
            t0 = t1 = pair_tile(p); name = 'pair'
        else:
            name = p['img']; t0, t1 = window(img(name), p['from']), window(img(name), p['to'])
        tile = Image.new('RGB', (TW * 2 + 6, TH + 22), (12, 12, 14))
        tile.paste(t0, (0, 22)); tile.paste(t1, (TW + 6, 22))
        ImageDraw.Draw(tile).text((4, 5), f'{ci + 1}-{j + 1} line {line}  {name}   start | end', fill=(255, 210, 90))
        tiles.append(tile)
cols = 3; rows = (len(tiles) + cols - 1) // cols; tw, th = tiles[0].size
sheet = Image.new('RGB', (cols * (tw + 10), rows * (th + 8)), (0, 0, 0))
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * (tw + 10), (i // cols) * (th + 8)))
sheet.save(out, quality=82)
print(out, len(tiles), 'shots', sheet.size)
