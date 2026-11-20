#!/usr/bin/env python3
"""Find free-to-use pictures on Wikimedia Commons for a video, with their licence.

Usage: find_images.py <out_dir> "<query 1>" "<query 2>" ...      or      find_images.py <out_dir> --spec <file.json>

A query is one of
  <words>                  full-text search of the Commons files, as always. `incategory:"<Commons category>"` lists
                           the files of a person, building or place (add a word or a year to narrow it).
  wiki: <name or Qid>      every picture ABOUT one thing (a person, an institution, a company, a building, a town, a
                           work), found through its Wikidata item: the item's own pictures, the pictures of its
                           Wikipedia articles (LANGS), the files of its Commons category and sub-categories, the
                           photos taken at its coordinates. `wiki: Friedrich Merz`, `wiki: Bundestag`, `wiki: Q567`.
                           This is where the real pictures of a subject are: ask it first.
  geo: <lat>,<lon> [<m>]   Commons photos taken around a point, whatever they are called: `geo: 52.5186,13.3762 300`
With --spec the file holds a JSON list of such strings and of
  {"q": "<query>", "want": "<what the picture must show, in English>", "keep": 12}      a query with its own wish

Ranking (17/11/2026). A query with a "want", and a full-text query in plain words, asks for 30 files, not 12, looks
at a small version of every one and keeps the 8 that fit the words best: CLIP (open_clip ViT-B/32, MIT; weights from
its GitHub release, kept in ~/.cache/find-images) scores picture against text ("want", else the query's own words),
and the order of the search counts a little too. The score is "match" in index.json and on the contact sheet (about
0.30 and more: it shows the thing; under 0.22: it does not). With a "want", pictures under 0.18 are dropped; ranked
pictures that look unsuitable for a general audience (Clip.UNFIT) are left out. Without torch/open_clip installed, or
with FIND_RANK=0, nothing is ranked and a query returns what it always returned: the first 8 of 12. Queries that list
files by construction (`wiki:`, `geo:`, `incategory:` and the other search keywords) and queries in a script CLIP
cannot read (Japanese …) keep their order unless they have a "want".

For every query: up to 8 pictures (24 for wiki:, 12 for geo:, or "keep"), keeping only licences that allow use in a
monetised video (public domain, CC0, CC BY, CC BY-SA), dropping files under 400 px (250 px for incategory: searches)
and duplicate scans of the same picture (also across earlier rounds listed in FIND_SEEN). Pictures are taken in the
standard sizes Commons serves freely (https://w.wiki/GHai), up to 1920 px wide, a few at a time; a host that
answers 429 (too many requests) is waited for as long as it asks, 90 s in a whole run at most, not again for every
query. Writes
<out_dir>/<k>-<n>.jpg, <out_dir>/index.json (query, file page, licence, author, credit line, date, size, source,
match; for wiki: the item found) and <out_dir>/sheet_<k>.jpg (contact sheet with numbers) so a person or Claude can
choose. A query whose search fails (timeout, connection reset, an answer that is not JSON, an HTTP error) is logged
and kept with no results and an "error" in index.json; only when every query fails does the script exit with an
error. Stdlib + Pillow (+ torch and open_clip_torch for the ranking).
"""
import http.client, io, json, os, re, sys, threading, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw

API = 'https://commons.wikimedia.org/w/api.php'
WIKIDATA = 'https://www.wikidata.org/w/api.php'
UA = 'NewsVideoFactory/0.1 (https://github.com/maihaianh2911-bit/germany-news-video-factory; licence-checked picture search)'
LANGS = ('en',)   # the Wikipedias wiki: reads (the channel's language; US cases are best covered there)
OK = re.compile(r'^(public domain|pd|cc0|cc[- ]by(-sa)?[- ]?\d|cc[- ]by(-sa)?$)', re.I)


NET = (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException)
WIKIMEDIA = threading.BoundedSemaphore(2)   # Wikimedia asks for few requests at a time, whatever runs in parallel here
PATIENCE = 90   # seconds a whole run waits for one host that answers 429 (too many requests), see get()
WAITED = {}     # host -> seconds waited so far in this run


def pause(e):
    """Seconds to wait after a 429: what the host asks for (Retry-After; Wikimedia: 16), 2 to 30; 10 when it does not say."""
    try: return min(30, max(2, int(e.headers.get('Retry-After'))))
    except Exception: return 10


def get(url, tries=4, timeout=60):
    """GET with retries: 429 (rate limit), 5xx and network errors (timeout, reset). After a 429 the host is given
    the time it asks for, but PATIENCE seconds in the whole run at most: once they are spent a request to that host
    is tried once, so a limit that lasts minutes costs one wait per run, not one for every query and picture."""
    host = urllib.parse.urlsplit(url).netloc
    gentle = host.endswith('wikimedia.org')
    for i in range(tries):
        try:
            if gentle: WIKIMEDIA.acquire()
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=timeout) as r:
                    return r.read()
            finally:
                if gentle: time.sleep(0.05); WIKIMEDIA.release()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1 and WAITED.get(host, 0) + pause(e) <= PATIENCE:
                WAITED[host] = WAITED.get(host, 0) + pause(e); time.sleep(pause(e)); continue
            if e.code in (500, 502, 503, 504) and i < tries - 1:
                time.sleep(8 * (i + 1)); continue
            raise
        except NET:
            if i < tries - 1:
                time.sleep(5 * (i + 1)); continue
            raise


def js(url):
    return json.loads(get(url))


def api(host=API, **p):
    """One MediaWiki query, as JSON. An error the API reports (bad coordinates, too many requests) fails the query
    instead of reading as "nothing found"."""
    d = js(host + '?' + urllib.parse.urlencode({'action': 'query', 'format': 'json', **p}))
    if isinstance(d, dict) and d.get('error'):
        raise RuntimeError(f"{d['error'].get('code')}: {str(d['error'].get('info'))[:120]}")
    return d


def pages(d):
    return list(((d or {}).get('query') or {}).get('pages', {}).values())


def strip(html):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html or '')).strip()


STD = (960, 1280, 1920, 3840)   # Commons serves these widths freely; other sizes and originals are rate-limited
SMALL = 330      # the small version looked at for the ranking (a standard Commons width too)
SIZED = re.compile(r'(?<=[/-])\d+(?=px-[^/]+$)')   # the width in a thumbnail URL: …/330px-A.jpg, …/lossy-page1-330px-A.tif.jpg
INFO = {'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': SMALL}


def results(pgs, source='commons', order=None):
    """Results from the pages of a Commons answer asked with INFO, in the order of the search (or of `order`, the
    list of titles asked for: the API answers those in its own order). Pictures only, under a licence that allows
    the video. thumb: the picture to keep, the largest standard size up to 1920 px (a file under 960 px is taken
    whole); preview: its 330 px version, for the ranking."""
    pgs = list(pgs)
    if order:
        pos = {t.replace('_', ' '): i for i, t in enumerate(order)}
        pgs.sort(key=lambda pg: pos.get(pg.get('title', ''), 1e9))
    else:
        pgs.sort(key=lambda pg: pg.get('index', 0))
    out = []
    for pg in pgs:
        ii = (pg.get('imageinfo') or [{}])[0]
        if ii.get('mime') not in ('image/jpeg', 'image/png', 'image/tiff'):
            continue
        md = ii.get('extmetadata') or {}
        lic = strip((md.get('LicenseShortName') or {}).get('value'))
        if not OK.search(lic):
            continue
        small = (ii.get('thumburl') or ii.get('url') or '').split('?')[0]
        w, url = ii.get('width') or 0, small
        if SIZED.search(small):   # a real thumbnail: the same file in another width
            top = [x for x in STD if x <= w and x <= 1920]
            if top or ii.get('mime') == 'image/tiff':   # a small TIFF: in its own width, as the JPEG Commons renders
                url = SIZED.sub(str(top[-1] if top else w), small, count=1)
            else:
                url = (ii.get('url') or small).split('?')[0]
        out.append({'title': pg['title'], 'page': ii.get('descriptionurl'), 'thumb': url,
                    'width': ii.get('width'), 'height': ii.get('height'), 'license': lic,
                    'artist': strip((md.get('Artist') or {}).get('value'))[:160],
                    'credit': strip((md.get('Credit') or {}).get('value'))[:160],
                    'date': strip((md.get('DateTimeOriginal') or {}).get('value'))[:60],
                    'description': strip((md.get('ImageDescription') or {}).get('value'))[:300],
                    'attribution_required': (md.get('AttributionRequired') or {}).get('value') == 'true',
                    'source': source, 'preview': small})
    return out


def search(q, n=12):
    """Full-text search of the Commons files, in the order of the search."""
    return results(pages(api(generator='search', gsrsearch=q, gsrnamespace=6, gsrlimit=min(50, n), **INFO)))


def batches(titles, n=50, size=6000):
    """The titles in groups one request can carry: 50 at most, and a short enough address (long or non-Latin names)."""
    group, used = [], 0
    for t in titles:
        cost = len(urllib.parse.quote(t)) + 3
        if group and (len(group) >= n or used + cost > size):
            yield group; group, used = [], 0
        group.append(t); used += cost
    if group: yield group


def files(titles, source):
    """Results for a list of Commons file titles, in that order (a file that is not on Commons, e.g. a non-free
    picture kept on one Wikipedia only, simply does not come back)."""
    out = []
    for group in batches(titles):
        out += results(pages(api(titles='|'.join(group), **INFO)), source, order=group)
    return out


def geo(q, n=50):
    """Commons photos taken around a point: "<lat>,<lon> [<radius in metres>]" (default 500 m, 10 km at most)."""
    m = re.match(r'^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)(?:\s+(\d+))?\s*m?\s*$', q)
    if not m: raise ValueError(f'geo: expects "<lat>,<lon> [<metres>]", got "{q}"')
    rad = min(10000, max(10, int(m.group(3) or 500)))
    d = api(generator='geosearch', ggscoord=f'{m.group(1)}|{m.group(2)}', ggsradius=rad, ggsnamespace=6,
            ggslimit=min(100, n * 2), **INFO)
    out, series = [], set()
    for r in results(pages(d), 'commons/geo'):
        key = re.sub(r'\d+', '#', r['title'])   # survey tiles and photo series differ in their numbers only: one of each
        if key in series: continue
        series.add(key); out.append(r)
    return out


# page furniture of Wikipedia articles and maps that show no place: never a picture of the thing
ICON = re.compile(r'(?i)(commons-logo|wik\w*[- ]logo|qsicon|oojs|red pog|loca\w+ map|\bicon\b|flag of|disambig|padlock|'
                  r'question book|ambox|edit-ltr|symbol \w+ vote|speaker|nuvola|crystal clear|\.svg$)')
FOUND = {}   # wiki: query -> the Wikidata item it was read as (for index.json: Claude checks it is the right thing)


def wiki(q, n=60):
    """Every picture about one thing, through its Wikidata item (see the module text). Most to the point first: the
    item's own pictures, the pictures of its Wikipedia articles, its Commons category, then photos taken there."""
    q = q.strip()
    qid = q if re.fullmatch(r'Q\d+', q) else None
    for lang in LANGS:   # the exact title of a Wikipedia article first: "Frankfurt (Oder)", "Michael Müller (Politiker, 1964)"
        if qid: break
        try:
            d = api(f'https://{lang}.wikipedia.org/w/api.php', titles=q, prop='pageprops', redirects=1)
        except Exception as ex:
            print(f'  wiki: {lang}.wikipedia.org {str(ex)[:80]}', flush=True); continue
        for pg in pages(d):
            pp = pg.get('pageprops') or {}
            if pp.get('wikibase_item') and 'disambiguation' not in pp: qid = pp['wikibase_item']
    for lang in LANGS:   # else the item called so
        if qid: break
        hits = js(WIKIDATA + '?' + urllib.parse.urlencode({'action': 'wbsearchentities', 'search': q, 'language': lang, 'uselang': lang,
                                                           'type': 'item', 'limit': 3, 'format': 'json'})).get('search', [])
        if hits: qid = hits[0]['id']
    if not qid:
        raise RuntimeError(f'wiki: no Wikidata item named "{q}" (try the title of its Wikipedia article, or a plain search)')
    ents = js(WIKIDATA + '?' + urllib.parse.urlencode({'action': 'wbgetentities', 'ids': qid, 'props': 'claims|sitelinks|labels|descriptions',
                                                       'languages': '|'.join(LANGS), 'format': 'json'})).get('entities') or {}
    e = ents.get(qid) or next(iter(ents.values()), {})
    if not e or 'missing' in e:
        raise RuntimeError(f'wiki: no Wikidata item {qid}')
    claims, links = e.get('claims') or {}, e.get('sitelinks') or {}
    val = lambda p: [c['mainsnak']['datavalue']['value'] for c in claims.get(p, []) if c.get('mainsnak', {}).get('datavalue')]
    first = lambda d: next((d[l]['value'] for l in LANGS if l in d), '')
    coord = (val('P625') or [None])[0]
    FOUND[q] = {'id': e.get('id', qid), 'label': first(e.get('labels') or {}), 'description': first(e.get('descriptions') or {}),
                **({'coord': [round(coord['latitude'], 5), round(coord['longitude'], 5)]} if coord else {})}
    # picture, grave, interior, aerial view, view at night
    own = ['File:' + v for p in ('P18', 'P1442', 'P5775', 'P8592', 'P3451') for v in val(p) if isinstance(v, str)]
    article = []
    for lang in LANGS:
        if lang + 'wiki' not in links: continue
        try:
            d = api(f'https://{lang}.wikipedia.org/w/api.php', titles=links[lang + 'wiki']['title'], prop='images', imlimit=500, redirects=1)
        except Exception as ex:
            print(f'  wiki: {lang}.wikipedia.org {str(ex)[:80]}', flush=True); continue
        for pg in pages(d):
            article += ['File:' + i['title'].split(':', 1)[1] for i in pg.get('images', [])]
    home = links.get('commonswiki', {}).get('title', '')
    cat = (val('P373') or [home[9:] if home.startswith('Category:') else ''])[0]
    seen, out = set(), []
    fresh = lambda titles: [t for t in dict.fromkeys(titles) if t.replace('_', ' ') not in seen and not ICON.search(t)]
    def add(titles, source):   # the files not listed yet, in the order given
        titles = fresh(titles)[:150]
        seen.update(t.replace('_', ' ') for t in titles)
        out.extend(files(titles, source))
    add(own + article, 'commons/wiki')
    members = lambda c, t, lim: [x['title'] for x in (api(list='categorymembers', cmtitle='Category:' + c, cmtype=t, cmlimit=lim).get('query') or {}).get('categorymembers', [])]
    if cat and len(out) < n:   # the category fills what is left: twice as many files as are missing (not every one is a free picture)
        need = 2 * (n - len(out))
        try:
            filed = members(cat, 'file', 100)
            for sub in members(cat, 'subcat', 12) if len(fresh(filed)) < need else []:
                if len(fresh(filed)) >= need: break
                filed += members(sub[9:], 'file', 50)
            add(fresh(filed)[:need], 'commons/category')
        except Exception as ex:   # the item's and the articles' pictures are still worth having
            print(f'  wiki: category {str(ex)[:80]}', flush=True)
    if coord and len(out) < n:   # the place itself, whatever the photos are called
        try: out += [r for r in geo(f"{coord['latitude']},{coord['longitude']} 400", 20) if r['title'] not in seen]
        except Exception as ex: print(f'  wiki: geo {str(ex)[:80]}', flush=True)
    return out[:n]


FIND = {'wiki': wiki, 'geo': geo}
# search keywords that list files instead of looking for words: such a query is not ranked against its own text
KEYWORD = re.compile(r'(?i)\b(incategory|deepcat|deepcategory|intitle|insource|hastemplate|haswbstatement|filetype|filemime|filew|fileh|fileres):')


def source_of(q):
    """(source, words) of a query string: "wiki: X" -> ("wiki", "X"), "geo: 52.5,13.4 300" -> ("geo", …). Anything
    else is a Commons search and stays whole: (None, q), also `incategory:"X"` and "Dr. Müller: Akte"."""
    m = re.match(r'^\s*(\w+):\s*(.+?)\s*$', q, re.S)
    return (m.group(1).lower(), m.group(2)) if m and m.group(1).lower() in FIND else (None, q)


class Clip:
    """Scores how well a picture fits a text (open_clip ViT-B/32, weights from its GitHub release, on the CPU)."""
    URL = 'https://github.com/mlfoundations/open_clip/releases/download/v0.2-weights/vit_b_32-quickgelu-laion400m_e32-46683a32.pt'
    # what a video for a general audience must not show by accident: pictures that look like one of these (0.21 and
    # more; ordinary pictures stay under 0.18) are dropped from ranked results
    UNFIT = ('a nude person', 'a woman in lingerie or underwear', 'an erotic photo')
    model = None; failed = False; unfit = None

    @classmethod
    def ready(cls):
        if cls.model is None and not cls.failed:
            path = os.environ.get('CLIP_MODEL') or os.path.expanduser('~/.cache/find-images/vit_b_32-quickgelu-laion400m_e32.pt')
            try:
                if os.environ.get('FIND_RANK', '1') == '0': raise RuntimeError('FIND_RANK=0')
                import torch, open_clip
                if not os.path.exists(path):
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    urllib.request.urlretrieve(cls.URL, path + '.part'); os.replace(path + '.part', path)
                model, _, pre = open_clip.create_model_and_transforms('ViT-B-32-quickgelu', pretrained=path)
                cls.model, cls.pre, cls.tok, cls.torch = model.eval(), pre, open_clip.get_tokenizer('ViT-B-32-quickgelu'), torch
            except Exception as e:
                cls.failed = True; print(f'ranking off, the first pictures of every search are kept ({str(e)[:90]})', flush=True)
                try: os.remove(path + '.part')   # half a download must not stay in the folder the workflow caches
                except OSError: pass
        return cls.model is not None

    @classmethod
    def scores(cls, images, text):
        """For every picture: how well it fits the text, and how much it looks like something not to show."""
        t = cls.torch
        with t.no_grad():
            fi = t.cat([cls.model.encode_image(t.stack([cls.pre(im) for im in images[i:i + 32]])) for i in range(0, len(images), 32)])
            fi /= fi.norm(dim=-1, keepdim=True)
            ft = cls.model.encode_text(cls.tok([text, 'a photo of ' + text])); ft /= ft.norm(dim=-1, keepdim=True)
            if cls.unfit is None:
                cls.unfit = cls.model.encode_text(cls.tok(list(cls.UNFIT))); cls.unfit /= cls.unfit.norm(dim=-1, keepdim=True)
            return (fi @ ft.T).max(dim=1).values.tolist(), (fi @ cls.unfit.T).max(dim=1).values.tolist()


def picture(url, tries=2, timeout=20):
    """One picture, decoded. Two short tries: a dead host costs 45 s at most, not minutes."""
    return Image.open(io.BytesIO(get(url, tries=tries, timeout=timeout))).convert('RGB')


MATCH_MIN = 0.18   # a query with a "want": pictures that fit it less are dropped (about 0.30: shows it; 0.15: something else)
UNFIT_MIN = 0.21   # looks like one of Clip.UNFIT


def ranked(found, text):
    """The results ordered by how well their small version fits the text (CLIP), the order of the search counting a
    little (0.004 per place: it decides between pictures CLIP finds alike, as for a name it does not know).
    Results whose small version cannot be loaded go last; pictures that look unsuitable (Clip.UNFIT) are left out.
    Sets r['match']. Returns (results, number left out)."""
    def small(r):
        try:
            im = picture(r['preview'], tries=1, timeout=15); im.thumbnail((448, 448)); return im   # one try: a slow host only loses its place
        except Exception:
            return None
    with ThreadPoolExecutor(6) as ex:
        ims = list(ex.map(small, found))
    ok = [(r, im) for r, im in zip(found, ims) if im is not None]
    if not ok: return found, 0
    fit, unfit = Clip.scores([im for _, im in ok], text)
    for (r, _), sc in zip(ok, fit):
        r['match'] = round(sc, 3)
    out = {id(r) for (r, _), u in zip(ok, unfit) if u >= UNFIT_MIN}
    best = sorted((r for r, _ in ok if id(r) not in out), key=lambda r: -(r['match'] - 0.004 * r.get('rank', 0)))
    return best + [r for r, im in zip(found, ims) if im is None], len(out)


def sheet(files, path, labels=None):
    """Numbered contact sheet; each tile says its size and licence so small or unusable files are seen at once, and
    under them where the picture comes from, its date and how well it fits what was asked."""
    try:
        from PIL import ImageFont
        font = ImageFont.load_default(size=16)
    except Exception:
        font = None
    tiles = []
    for i, f in enumerate(files, 1):
        im = Image.open(f).convert('RGB'); im.thumbnail((360, 350))
        t = Image.new('RGB', (380, 410), (20, 20, 24)); t.paste(im, ((380 - im.width) // 2, 8))
        for k, row in enumerate((labels or {}).get(f, f'#{i}').split('\n')):
            ImageDraw.Draw(t).text((10, 364 + k * 20), row, fill=(255, 210, 90), font=font)
        tiles.append(t)
    if not tiles:
        return
    cols = 4; rows = (len(tiles) + cols - 1) // cols
    s = Image.new('RGB', (cols * 380, rows * 410), (10, 10, 12))
    for i, t in enumerate(tiles):
        s.paste(t, ((i % cols) * 380, (i // cols) * 410))
    s.save(path, quality=85)


MIN_SIDE = 400   # shorter side in pixels: smaller files only look blurred in the video
MIN_SIDE_CAT = 250   # incategory: searches target one person or work, whose small documents (a 1914 cover)
                     # still serve as a framed print
KEEP, KEEP_WIKI, KEEP_GEO = 8, 24, 12   # pictures kept per query: a search, wiki:, geo: (or the query's "keep")
FETCH, DEEP = 12, 30   # files asked from a search: as always (dropped ones are replaced), and when they are ranked


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


def parts(q):
    """(query, want, keep) of one entry of the list: a string, or {"q": …, "want": …, "keep": …}."""
    if isinstance(q, str):
        return q, None, None
    if not isinstance(q, dict) or not isinstance(q.get('q'), str) or not q['q'].strip():
        raise ValueError('a query is a string or {"q": "<query>", "want": "<what the picture must show>", "keep": <number>}')
    keep = q.get('keep')
    if keep is not None and (isinstance(keep, bool) or not isinstance(keep, int) or not 1 <= keep <= 40):
        raise ValueError('"keep" is a number from 1 to 40')
    return q['q'], (str(q.get('want') or '').strip() or None), keep


def main():
    out, queries = sys.argv[1], sys.argv[2:]
    if queries[:1] == ['--spec']:
        queries = json.load(open(queries[1], encoding='utf-8'))
    os.makedirs(out, exist_ok=True)
    index, kept_hashes, failed = [], seen_hashes(), 0
    dropped = {'small': 0, 'duplicate': 0, 'unfit': 0, 'unsuitable': 0, 'lost': 0}
    for k, q in enumerate(queries, 1):
        want = src = None
        try:
            q, want, keep = parts(q)
            src, words = source_of(q)
            lim = MIN_SIDE_CAT if q.strip().lower().startswith('incategory:') else MIN_SIDE
            keep = keep or (KEEP_WIKI if src == 'wiki' else KEEP_GEO if src == 'geo' else KEEP)
            # ranked against "want"; else a search in plain words against those words, when CLIP can read them (it
            # reads English and other Latin-script words; a query in Japanese or Cyrillic keeps the search's order)
            plain = src is None and not KEYWORD.search(q) and not re.search(r'[^\x00-\u024f\u2000-\u206f]', q)
            rank = bool(want or plain) and Clip.ready()
            res = FIND[src](words, max(30, keep * 5 // 2)) if src else search(q, n=DEEP if rank else FETCH)
            for i, r in enumerate(res): r['rank'] = i
            found = [r for r in res if min(r.get('width') or 0, r.get('height') or 0) >= lim]
            dropped['small'] += len(res) - len(found)
            n_found = len(found)
            if rank and len(found) > 1:
                found, n_out = ranked(found, want or words); dropped['unsuitable'] += n_out
                if want:   # asked for by a description: what does not show it is no use
                    n_all = len(found); found = [r for r in found if r.get('match', 1) >= MATCH_MIN]
                    dropped['unfit'] += n_all - len(found)
        except Exception as e:   # one bad query must not lose the others: log it, keep it empty
            err = f'{type(e).__name__}: {str(e)[:150]}'
            q = q if isinstance(q, str) else json.dumps(q, ensure_ascii=False)
            print(f'{k}. {q}: search failed ({err}), no pictures for this query', flush=True)
            index.append({'k': k, 'query': q, 'results': [], **({'want': want} if want else {}), 'error': err}); failed += 1
            continue

        def full(r):
            try: return picture(r['thumb'])
            except Exception as e:
                r['error'] = f'{type(e).__name__}: {str(e)[:100]}'; return None
        kept, lost = [], []   # [(result, image, hash)] in search order; a duplicate inside this query keeps the bigger file
        for i in range(0, len(found), 6):
            if len(kept) >= keep:
                break
            batch = found[i:i + 6]
            with ThreadPoolExecutor(3) as ex:   # a few at a time: Wikimedia asks for it
                ims = list(ex.map(full, batch))
            for r, im in zip(batch, ims):
                if len(kept) >= keep:
                    break
                if im is None:
                    lost.append(r); continue
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
        dropped['lost'] += len(lost)
        paths, labels, rows = [], {}, []
        for n, (r, im, h) in enumerate(kept, 1):
            im.thumbnail((4000, 4000))   # enough for crops of a detail; keeps the renders branch small
            p = f'{out}/{k}-{n}.jpg'; im.save(p, quality=90)
            r['file'] = p[len(out) + 1:]; paths.append(p)
            rows.append({key: v for key, v in r.items() if key not in ('preview', 'rank', 'error')})
            lic = re.sub(r'(?i)public domain', 'PD', r['license'])
            fit = f"  ~{r['match']:.2f}" if 'match' in r else ''   # "~": the sheet's font has no "≈"
            labels[p] = f"#{n}  {im.width}x{im.height}  {lic}"[:40] + '\n' + f"{r['source']}  {r['date']}"[:40 - len(fit)] + fit
        kept_hashes += [h for _, _, h in kept]
        sheet(paths, f'{out}/sheet_{k}.jpg', labels)
        about = FOUND.get(words) if src == 'wiki' else None
        err = None
        if lost and not kept:   # found, but no picture came: not "nothing found" (Claude repeats the query in the next round)
            err = f"{len(lost)} pictures found, none could be downloaded ({lost[0].get('error', '?')})"; failed += 1
        index.append({'k': k, 'query': q, 'results': rows, 'candidates': n_found, **({'want': want} if want else {}),
                      **({'wikidata': about} if about else {}), **({'error': err} if err else {})})
        print(f'{k}. {q}: {len(rows)} kept of {n_found}' + (f', {len(lost)} could not be downloaded' if lost else '')
              + (f' = {about["id"]} {about["label"]}: {about["description"]}' if about else ''), flush=True)
    json.dump(index, open(f'{out}/index.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f"dropped: {dropped['small']} too small, {dropped['duplicate']} duplicates, {dropped['unfit']} not showing what was asked, "
          f"{dropped['unsuitable']} unsuitable, {dropped['lost']} not downloaded; {failed} queries failed")
    if queries and failed == len(queries):
        sys.exit('every search failed (Wikimedia Commons unreachable?)')


if __name__ == '__main__':
    main()
