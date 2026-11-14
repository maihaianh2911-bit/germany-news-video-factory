#!/usr/bin/env python3
"""Crop, grade and size the pictures chosen in picks.json. Usage: prep.py <picks.json> <img_root> <out_dir>

picks.json "images": {"<name>": {"src": "<round>/<file>" (from the image search) or "own/<file>" (news/<N>/own/),
"crop": [x0, y0, x1, y1] (0..1, optional), "mode": "sepia" | "color" | "keep", "sat": 0.92, "vignette": 0.0,
"page": "<source URL>" (optional, only used by build.py for credits.txt)}}
→ <out_dir>/<name>.jpg. sepia: black-and-white sources toned to the video's warm palette; color: slight
desaturation, warmth and contrast so paintings from different centuries sit together.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageFilter


def rounds_used(picks):
    """Search rounds the chosen pictures come from: {"1", "2"} for "1/2-1.jpg" and "2/1-3.jpg" (not "own")."""
    return {it['src'].split('/')[0] for it in picks.get('images', {}).values() if '/' in it.get('src', '')} - {'own'}


def missing_sources(picks, root):
    """Chosen pictures ("src") that are not under <root>, in picks order."""
    return [it.get('src', '?') for it in picks.get('images', {}).values() if not os.path.isfile(os.path.join(root, it.get('src', '?')))]


def prepare(it, root):
    """One picture of picks.json "images", cropped and graded (PIL image)."""
    im = Image.open(os.path.join(root, it['src'])).convert('RGB')
    if it.get('crop'):
        x0, y0, x1, y1 = it['crop']; W, H = im.size
        im = im.crop((round(x0 * W), round(y0 * H), round(x1 * W), round(y1 * H)))
    W, H = im.size
    short = it.get('min_short', 1150)
    if min(W, H) < short:  # soft sources are enlarged here so the panel never shows browser scaling
        k = short / min(W, H); im = im.resize((round(W * k), round(H * k)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2.0, percent=60, threshold=2))
    if max(im.size) > 2600:
        k = 2600 / max(im.size); im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32) / 255
    mode = it.get('mode', 'color')
    if mode == 'sepia':
        l = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
        lo, hi = np.percentile(l, 1), np.percentile(l, 99.3)
        l = np.clip((l - lo) / max(1e-3, hi - lo), 0, 1)
        l = l * l * (3 - 2 * l) * 0.35 + l * 0.65
        dark, light = np.array([0.07, 0.055, 0.04]), np.array([0.93, 0.87, 0.75])
        a = dark + (light - dark) * l[..., None]
    elif mode == 'color':
        g = a.mean(axis=2, keepdims=True); a = g + (a - g) * it.get('sat', 0.92)
        a = np.clip(a * np.array([1.02, 1.0, 0.96]), 0, 1)
        a = a * a * (3 - 2 * a) * 0.25 + a * 0.75
    v = it.get('vignette', 0.0)
    if v:
        H, W = a.shape[:2]; yy, xx = np.mgrid[0:H, 0:W]
        r = np.sqrt(((xx / W - 0.5) * 2) ** 2 + ((yy / H - 0.5) * 2) ** 2) / np.sqrt(2)
        a = a * (1 - v * np.clip(r - 0.35, 0, 1)[..., None] ** 1.5)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


if __name__ == '__main__':
    picks, root, out = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out, exist_ok=True)
    for name, it in json.load(open(picks, encoding='utf-8'))['images'].items():
        prepare(it, root).save(os.path.join(out, f'{name}.jpg'), quality=90)
        print(name, Image.open(os.path.join(out, f'{name}.jpg')).size)
