#!/usr/bin/env python3
"""One contact sheet of the finished video for the final check: every shot (middle of its time on screen, with its
subtitle), labelled chapter-shot, picture name and time. Usage: sheet.py <video.mp4> <plan.json> <picks.json> <out.jpg>"""
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
        im = frame(t, f'{tmp}/f.png').resize((216, 384))
        name = picks['chapters'][ci]['pics'][j]['img']
        ImageDraw.Draw(im).rectangle((0, 0, 216, 22), fill=(0, 0, 0))
        ImageDraw.Draw(im).text((6, 5), f"{ci + 1}-{j + 1} {name}  {p['s']:.0f}s", fill=(255, 210, 90))
        tiles.append(im)
cols = min(8, len(tiles)); rows = (len(tiles) + cols - 1) // cols
W = cols * 222; H = rows * 390
s = Image.new('RGB', (W, H), (12, 12, 14))
for i, t in enumerate(tiles): s.paste(t, ((i % cols) * 222, (i // cols) * 390))
s.save(out, quality=85)
print(out, len(tiles), 'shots')
