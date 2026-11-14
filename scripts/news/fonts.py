#!/usr/bin/env python3
"""Add the fonts a plan needs. Usage: fonts.py <plan.json> <fontsource_dir> <public_dir>

<fontsource_dir> holds the unpacked npm packages @fontsource-variable/source-serif-4 and source-sans-3 and
@fontsource/courier-prime (folders source-serif-4/, source-sans-3/, courier-prime/). Only the unicode-range chunks that contain characters of this video are
copied to <public_dir>/news/fonts/ and listed in plan["fonts"] (NewsV registers them with FontFace).
"""
import json, os, re, shutil, sys

plan_path, src, pub = sys.argv[1], sys.argv[2], sys.argv[3]
plan = json.load(open(plan_path, encoding='utf-8'))
chars = set(json.dumps(plan, ensure_ascii=False)) | set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ÄÖÜäöüß—–„“‚‘«».,:;!?()/ ')
os.makedirs(f'{pub}/news/fonts', exist_ok=True); out = []
for fam, pkg, css in [('Source Serif 4', 'source-serif-4', 'index.css'), ('Source Serif 4', 'source-serif-4', 'wght-italic.css'),
                      ('Source Sans 3', 'source-sans-3', 'index.css'), ('Courier Prime', 'courier-prime', 'index.css')]:
    base = os.path.join(src, pkg)
    for blk in re.findall(r'@font-face\s*{(.*?)}', open(f'{base}/{css}').read(), re.S):
        style = re.search(r'font-style:\s*(\w+)', blk).group(1)
        f = re.search(r"url\(\./files/([^)]+\.woff2)\)", blk).group(1)
        ur = re.search(r'unicode-range:\s*([^;]+);', blk).group(1).strip()
        rs = []
        for part in ur.split(','):
            part = part.strip().replace('U+', '')
            a, b = part.split('-') if '-' in part else (part, part); rs.append((int(a, 16), int(b, 16)))
        if any(any(a <= ord(c) <= b for a, b in rs) for c in chars):
            shutil.copy(f'{base}/files/{f}', f'{pub}/news/fonts/{f}'); out.append({'family': fam, 'file': f'news/fonts/{f}', 'range': ur, 'style': style})
plan['fonts'] = out
json.dump(plan, open(plan_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'font chunks')
