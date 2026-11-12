#!/usr/bin/env python3
"""Find free-to-use pictures on Wikimedia Commons for a video, with their licence.

Usage: find_images.py <out_dir> "<query 1>" "<query 2>" ...
For every query: up to 8 files (12 searched in the File namespace), keeping only licences that allow use in a
monetised video (public domain, CC0, CC BY, CC BY-SA), dropping files under 400 px (250 px for incategory: searches) and duplicate scans of the same
picture (also across earlier rounds listed in FIND_SEEN). Writes <out_dir>/<k>-<n>.jpg (up to 2000 px wide),
<out_dir>/index.json (query, file page, licence, author, credit line, size) and <out_dir>/sheet_<k>.jpg
(contact sheet with numbers) so a person or Claude can choose. Stdlib + Pillow.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request
from PIL import Image, ImageDraw

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'NewsVideoFactory/0.1 (licence-checked picture search)'
OK = re.compile(r'^(public domain|pd|cc0|cc[- ]by(-sa)?[- ]?\d|cc[- ]by(-sa)?$)', re.I)


def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(10 * (i + 1)); continue
            raise


def strip(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()


def search(q, n=8):
    p = {'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': q, 'gsrnamespace': 6, 'gsrlimit': n,
         'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 2000, 'maxlag': 5}
    d = json.loads(get(API + '?' + urllib.parse.urlencode(p)))
    pages = sorted((d.get('query') or {}).get('pages', {}).values(), key=lambda x: x.get('index', 0))
    out = []
    for pg in pages:
        ii = (pg.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png', 'image/tiff'):
            continue
        md = ii.get('extmetadata') or {}
        lic = strip((md.get('LicenseShortName') or {}).get('value'))
        if not OK.search(lic):
            continue
        out.append({'title': pg['title'], 'page': ii.get('descriptionurl'), 'thumb': ii.get('thumburl') or ii.get('url'),
                    'width': ii.get('width'), 'height': ii.get('height'), 'license': lic,
                    'artist': strip((md.get('Artist') or {}).get('value'))[:160],
                    'credit': strip((md.get('Credit') or {}).get('value'))[:160],
                    'date': strip((md.get('DateTimeOriginal') or {}).get('value'))[:60],
                    'description': strip((md.get('ImageDescription') or {}).get('value'))[:300],
                    'attribution_required': (md.get('AttributionRequired') or {}).get('value') == 'true'})
    return out


def sheet(files, path, labels=None):
    """Numbered contact sheet; each tile says its size and licence so small or unusable files are seen at once."""
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=17)
    except Exception:
        font = None
    tiles = []
    for i, f in enumerate(files, 1):
        im = Image.open(f).convert('RGB'); im.thumbnail((360, 360))
        t = Image.new('RGB', (380, 400), (20, 20, 24)); t.paste(im, ((380 - im.width) // 2, 10))
        ImageDraw.Draw(t).text((10, 374), (labels or {}).get(f, f'#{i}'), fill=(255, 210, 90), font=font); tiles.append(t)
    if not tiles:
        return
    cols = 4; rows = (len(tiles) + cols - 1) // cols
    s = Image.new('RGB', (cols * 380, rows * 400), (10, 10, 12))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % cols) * 380, (i // cols) * 400))
    s.save(path, quality=85)


MIN_SIDE = 400   # shorter side in pixels: smaller files only look blurred in the video
MIN_SIDE_CAT = 250   # incategory: searches target one person or work, whose small documents (a 1914 cover)
                     # still serve as a framed print
KEEP = 8         # pictures kept per query (12 are fetched, so dropped ones are replaced)


def dhash(im, n=8):
    """64-bit difference hash: two scans of the same painting differ in a few bits only."""
    if hasattr(im, 'draft'): im.draft('L', (256, 256))   # fast JPEG decode at reduced size
    g = im.convert('L'); g.thumbnail((256, 256)); g = g.resize((n + 1, n), Image.LANCZOS)
    px = list(g.tobytes())
    return sum(1 << i for i in range(n * n) if px[(i // n) * (n + 1) + i % n] > px[(i // n) * (n + 1) + i % n + 1])


def same(a, b):
    return bin(a ^ b).count('1') <= 10


def seen_hashes():
    """Pictures of earlier search rounds of the same video (FIND_SEEN = dirs separated by ':') are not shown again."""
    hs = []
    for d in filter(None, os.environ.get('FIND_SEEN', '').split(':')):
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if re.match(r'^\d+-\d+\.jpg$', f):
                try: hs.append(dhash(Image.open(os.path.join(d, f))))
                except Exception: pass
    return hs


def main():
    out, queries = sys.argv[1], sys.argv[2:]
    os.makedirs(out, exist_ok=True)
    index, kept_hashes, dropped = [], seen_hashes(), {'small': 0, 'duplicate': 0}
    for k, q in enumerate(queries, 1):
        lim = MIN_SIDE_CAT if q.strip().lower().startswith('incategory:') else MIN_SIDE
        found = [r for r in search(q, n=12) if min(r.get('width') or 0, r.get('height') or 0) >= lim]
        dropped['small'] += 12 - len(found)
        kept = []   # [(result, image, hash)] in search order; a duplicate inside this query keeps the bigger file
        for r in found:
            if len(kept) >= KEEP:
                break
            try:
                im = Image.open(io.BytesIO(get(r['thumb']))).convert('RGB')
            except Exception as e:
                r['error'] = str(e)[:120]; continue
            finally:
                time.sleep(1)
            h = dhash(im)
            if any(same(h, x) for x in kept_hashes):
                dropped['duplicate'] += 1; continue
            twin = next((i for i, (_, _, kh) in enumerate(kept) if same(h, kh)), None)
            if twin is not None:
                dropped['duplicate'] += 1
                if im.width * im.height > kept[twin][1].width * kept[twin][1].height:
                    kept[twin] = (r, im, h)
                continue
            kept.append((r, im, h))
        files, labels, results = [], {}, []
        for n, (r, im, h) in enumerate(kept, 1):
            im.thumbnail((4000, 4000))   # enough for crops of a detail; keeps the renders branch small
            p = f'{out}/{k}-{n}.jpg'; im.save(p, quality=90)
            r['file'] = p[len(out) + 1:]; files.append(p); results.append(r)
            lic = re.sub(r'(?i)public domain', 'PD', r['license'])
            labels[p] = f"#{n}  {r.get('width')}x{r.get('height')}  {lic}"[:40]
        kept_hashes += [h for _, _, h in kept]
        sheet(files, f'{out}/sheet_{k}.jpg', labels)
        index.append({'k': k, 'query': q, 'results': results})
        print(f'{k}. {q}: {len(results)} kept')
        time.sleep(2)
    json.dump(index, open(f'{out}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"dropped: {dropped['small']} too small, {dropped['duplicate']} duplicates")


if __name__ == '__main__':
    main()
