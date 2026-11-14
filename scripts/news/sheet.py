#!/usr/bin/env python3
"""One contact sheet of the finished video for the final check: the picture panel of every shot (middle of its
time on screen), labelled chapter-shot and picture name, plus two full frames. Usage: sheet.py <video.mp4> <plan.json> <picks.json> <out.jpg>"""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import ff

video, plan, picks, out = sys.argv[1:5]
plan = json.load(open(plan, encoding='utf-8')); picks = json.load(open(picks, encoding='utf-8'))
tmp = tempfile.mkdtemp()
def frame(t, path):
    ff.run('-ss', f'{t:.2f}', '-i', video, '-frames:v', '1', path)
    return Image.open(path).convert('RGB')
tiles = []
for ci, c in enumerate(plan['chapters']):
    for j, p in enumerate(c['pics']):
        t = min(p['e'] - 0.3, max(p['s'] + 0.9, (p['s'] + p['e']) / 2))
        im = frame(t, f'{tmp}/f.png').crop((0, 0, 1080, 1000)).resize((324, 300))
        src = picks['chapters'][ci]['pics'][j]
        name = src.get('img') or 'pair'
        ImageDraw.Draw(im).rectangle((0, 0, 324, 22), fill=(0, 0, 0))
        ImageDraw.Draw(im).text((6, 5), f"{c['num']}-{j + 1} {name}  {p['s']:.0f}s", fill=(255, 210, 90))
        tiles.append(im)
cols = 6; rows = (len(tiles) + cols - 1) // cols
full = [frame(plan['duration'] * f, f'{tmp}/g.png').resize((324, 576)) for f in (0.3, 0.75)]
W = cols * 330; H = rows * 306 + 582
s = Image.new('RGB', (W, H), (12, 12, 14))
for i, t in enumerate(tiles): s.paste(t, ((i % cols) * 330, (i // cols) * 306))
for i, f in enumerate(full): s.paste(f, (i * 330, rows * 306))
s.save(out, quality=85)
print(out, len(tiles), 'shots')
