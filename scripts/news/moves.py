#!/usr/bin/env python3
"""The catalogue of camera moves of the news videos ("bảng cách edit", AGENT_NEWS.md §2.5).

A shot of picks.json names a move instead of free numbers: {"img": "merz", "move": "tien-gan", "focus": [0.5, 0.35],
"why": "câu nhắc tên Merz"}. expand() turns the name into the camera start and end ("from"/"to": zoom z and the
point x, y of the picture held at the panel centre) for that picture's size and the shot's length, so every move
has the same calm speed whatever the picture, never runs into the picture's edge and ends on the subject.
An explicit "from"/"to" in the shot still wins. No dependencies: used by build.py, preview.py, sheet.py and the tests.
"""
W, PH = 1080, 1000          # the picture panel of NewsV
FOCUS = (0.5, 0.45)         # default subject point: a little above the centre (faces)
MAX_FADE = 1.5

# name → (Vietnamese label for the owner, what it looks like). Order = order of the table in AGENT_NEWS.md.
MOVES = {
    'tien-gan':   ('tiến gần', 'slow push-in towards the subject (about +3 % per second, +10…20 %)'),
    'chi-tiet':   ('soi chi tiết', 'from the whole picture strongly into one detail (+25…45 %)'),
    'lui-ra':     ('lùi ra', 'starts close on the subject and pulls back to the whole picture, the subject kept in frame'),
    'luot-phai':  ('lướt sang phải', 'steady pan from left to right, no zoom change'),
    'luot-trai':  ('lướt sang trái', 'steady pan from right to left, no zoom change'),
    'nang-len':   ('nâng lên', 'tilt up: from the foot of the picture to its top'),
    'ha-xuong':   ('hạ xuống', 'tilt down: from the top of the picture to its foot'),
    'dung-yen':   ('đứng yên', 'held almost still (+3 %), the whole picture readable'),
    'troi-nhe':   ('trôi nhẹ', 'slightly closer, a small slow sideways drift with a light push that ends on the subject'),
}
CUSTOM = 'tự chỉnh'         # label of a shot with hand-written from/to and no move


def names():
    return ', '.join(MOVES)


def half(w, h, z):
    """Half of the visible window as a share of the picture (x, y) at zoom z: the centre can go from half to 1 - half."""
    c = max(W / w, PH / h) * z
    return W / (w * c) / 2, PH / (h * c) / 2


def cam(w, h, z, x, y):
    """A camera at zoom z looking at (x, y), moved inside the picture so the panel never shows past an edge."""
    hx, hy = half(w, h, z)
    return {'z': round(z, 3), 'x': round(min(1 - hx, max(hx, x)), 4), 'y': round(min(1 - hy, max(hy, y)), 4)}


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


# How far each move travels: usually RATE per second, never less than LEAST (so a short shot still visibly moves:
# the speed goes up), never more than MOST, and never faster than CAP per second (the sober limit). A shot so short
# that CAP does not reach LEAST is "too short for its move": the preview warns and suggests dung-yen.
# Zoom moves count in zoom (0.10 = +10 %), pans, tilts and the drift in panel widths/heights.
SPEED = {            # LEAST, RATE, MOST, CAP
    'tien-gan':  (0.10, 0.028, 0.20, 0.05),
    'chi-tiet':  (0.25, 0.070, 0.45, 0.12),
    'lui-ra':    (0.18, 0.050, 0.32, 0.09),
    'luot-phai': (0.25, 0.085, 9.0, 0.125), 'luot-trai': (0.25, 0.085, 9.0, 0.125),
    'nang-len':  (0.25, 0.085, 9.0, 0.125), 'ha-xuong':  (0.25, 0.085, 9.0, 0.125),
    'troi-nhe':  (0.12, 0.040, 0.30, 0.07),
}
MAX_SLIDE_Z = 1.45   # a pan or tilt zooms in at most this far to make room to travel
KEEP = 0.75          # the subject stays inside this share of the frame during chi-tiet and lui-ra


def amount(name, d):
    least, rate, most, cap = SPEED[name]
    return min(max(least, min(rate * d, most)), cap * d)


def too_short(name, dur):
    """True when the shot is too short for the move to travel its least visible distance at a sober speed."""
    return name in SPEED and SPEED[name][3] * max(float(dur), 1.0) < SPEED[name][0] - 1e-9


def slide(name, w, h, d, fx, fy, axis, sign):
    """A pan (axis 0) or tilt (axis 1) through the focus. The picture is zoomed in as far as needed (up to
    MAX_SLIDE_Z) to have room for the travel this shot's length asks for: a tilt on a landscape picture, which has
    no room at all at normal size, still travels."""
    want = amount(name, d)                                   # in panel sizes
    base = 2 * half(w, h, 1.0)[axis]                         # share of the picture the panel shows at z = 1
    z = clamp(base * (1 + want), 1.06, MAX_SLIDE_Z)          # room 1 - base/z must hold want·base/z
    hv = half(w, h, z)[axis]; room = 1 - 2 * hv
    travel = min(room, want * 2 * hv)                        # share of the picture the centre moves
    f = (fx, fy)[axis]
    a = clamp(f - travel / 2, hv, 1 - hv - travel); b = a + travel
    if sign < 0: a, b = b, a
    return (cam(w, h, z, a, fy), cam(w, h, z, b, fy)) if axis == 0 else (cam(w, h, z, fx, a), cam(w, h, z, fx, b))


def wide_cam(w, h, fx, fy, wide):
    """The whole-picture end of chi-tiet / lui-ra (z = 1): centred on `wide` when given, else halfway between the
    picture's centre and the subject, and always moved so the subject is inside the middle KEEP of the frame.
    With both ends holding the subject, it stays in the frame for the whole move."""
    cx, cy = wide or (0.5 + (fx - 0.5) * 0.5, 0.5 + (fy - 0.5) * 0.5)
    hx, hy = half(w, h, 1.0)
    cx = clamp(cx, fx - KEEP * hx, fx + KEEP * hx); cy = clamp(cy, fy - KEEP * hy, fy + KEEP * hy)
    return cam(w, h, 1.0, cx, cy)


def expand(name, w, h, dur, focus=None, wide=None):
    """(from, to) of move `name` for a prepared picture of w×h pixels shown for dur seconds, subject at focus (x, y).
    wide (x, y), optional: where the whole-picture end of chi-tiet / lui-ra looks (to take in a second subject)."""
    if name not in MOVES:
        raise ValueError(f'unknown move "{name}" — valid moves: {names()}')
    fx, fy = focus or FOCUS
    d = max(float(dur), 1.0)
    if name == 'tien-gan':
        return cam(w, h, 1.0, fx, fy), cam(w, h, 1 + amount(name, d), fx, fy)
    if name == 'chi-tiet':
        return wide_cam(w, h, fx, fy, wide), cam(w, h, 1 + amount(name, d), fx, fy)
    if name == 'lui-ra':
        return cam(w, h, 1 + amount(name, d), fx, fy), wide_cam(w, h, fx, fy, wide)
    if name == 'luot-phai': return slide(name, w, h, d, fx, fy, 0, 1)
    if name == 'luot-trai': return slide(name, w, h, d, fx, fy, 0, -1)
    if name == 'ha-xuong': return slide(name, w, h, d, fx, fy, 1, 1)
    if name == 'nang-len': return slide(name, w, h, d, fx, fy, 1, -1)
    if name == 'dung-yen':
        return cam(w, h, 1.0, fx, fy), cam(w, h, 1.03, fx, fy)
    # troi-nhe: a small drift with a slight push that arrives on the subject, from the side with more room
    z0, z1 = 1.08, 1.12
    hx = half(w, h, z0)[0]
    step = min(1 - 2 * hx, amount(name, d) * 2 * hx)
    end = clamp(fx, hx, 1 - hx)
    start = end - step if end - step >= hx else min(1 - hx, end + step)
    return cam(w, h, z0, start, fy), cam(w, h, z1, end, fy)


def travel(a, b, w, h):
    """How far the centre moves between two cameras, in panel sizes (x, y)."""
    hx, hy = half(w, h, (a['z'] + b['z']) / 2)
    return abs(b['x'] - a['x']) / (2 * hx), abs(b['y'] - a['y']) / (2 * hy)


def warnings(shot, w, h, dur):
    """What the preview should tell about a shot's move (English, for Claude; [] = fine)."""
    m = shot.get('move')
    if m not in MOVES or 'pair' in shot or ('from' in shot and 'to' in shot):
        return []
    out = []
    if too_short(m, dur):
        least = SPEED[m][0] / SPEED[m][3]
        out.append(f'{dur:.1f} s is too short for {m} (needs {least:.1f} s to show): use dung-yen, or give the picture more lines')
    if m in ('chi-tiet', 'lui-ra'):
        fx, fy = shot.get('focus') or FOCUS
        wc = wide_cam(w, h, fx, fy, shot.get('wide'))
        if shot.get('wide') and (abs(wc['x'] - shot['wide'][0]) > 0.02 or abs(wc['y'] - shot['wide'][1]) > 0.02):
            out.append(f'{m}: "wide" {shot["wide"]} would lose the subject at {[fx, fy]}; the frame was moved to '
                       f'[{wc["x"]:.2f}, {wc["y"]:.2f}] (a square panel cannot hold both: choose the wide point nearer the subject)')
    return out


def check(shot, where):
    """Problems of one shot's edit fields as text ([] = fine). where: e.g. 'cảnh 1-3'."""
    bad = []
    m = shot.get('move')
    if m is not None and m not in MOVES:
        bad.append(f'{where}: không có kiểu "{m}" — các kiểu dùng được: {names()}')
    if 'pair' in shot:
        if m is not None: bad.append(f'{where}: cảnh "pair" (hai ảnh đóng khung) không dùng "move"')
    elif m is None and not ('from' in shot and 'to' in shot):
        bad.append(f'{where}: cần "move" (một trong: {names()}) hoặc đủ cả "from" và "to"')
    for key in ('focus', 'wide'):
        f = shot.get(key)
        if f is not None and not (isinstance(f, (list, tuple)) and len(f) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in f)):
            bad.append(f'{where}: "{key}" phải là [x, y] trong khoảng 0–1')
    fd = shot.get('fade')
    if fd is not None and not (isinstance(fd, (int, float)) and not isinstance(fd, bool) and 0 <= fd <= MAX_FADE):
        bad.append(f'{where}: "fade" phải là số giây từ 0 (cắt thẳng) đến {MAX_FADE}')
    if 'why' in shot and not isinstance(shot['why'], str):
        bad.append(f'{where}: "why" phải là một câu ngắn')
    return bad


def check_all(picks):
    return [b for ci, c in enumerate(picks.get('chapters', [])) for j, p in enumerate(c.get('pics', [])) for b in check(p, f'cảnh {ci + 1}-{j + 1}')]


def camera(shot, w, h, dur):
    """(from, to) of a shot: the move's preset, with an explicit "from"/"to" of the shot winning."""
    if shot.get('move'):
        a, b = expand(shot['move'], w, h, dur, shot.get('focus'), shot.get('wide'))
        return shot.get('from', a), shot.get('to', b)
    return shot['from'], shot['to']


def label(shot):
    """What the sheets print for a shot: the move's name, 'pair', or '-' for hand-written numbers."""
    return 'pair' if 'pair' in shot else shot.get('move') or '-'


# ---- timing of the shots (the same rules as build.py; tests/news_smoke.py checks that both agree)
END = ('.', '!', '?', '…', '“', '"', '«', '»')


def shot_times(chapters, picks_chapters, dur, text):
    """[[(start, end, line), …] per chapter]: when each shot is on screen and the line it starts on.
    dur/text: {line number: seconds / words} (measured voice, or estimate())."""
    t, out = 0.0, []
    for ci, (c, pc) in enumerate(zip(chapters, picks_chapters)):
        a, b = c['lines']; s = t; x = s + (1.0 if ci == 0 else 0.8); starts = []
        for i in range(a, b + 1):
            starts.append(x)
            x += dur[i] + (0.45 if text[i].rstrip().endswith(END) else 0.25)
        e = x + (2.6 if ci == len(chapters) - 1 else 0.7)
        pics = pc['pics']; n = len(pics); bounds, at = [s], [a]
        for j in range(1, n):
            li = pics[j].get('at') or a + round(j * (b - a + 1) / n)
            k = min(len(starts) - 1, max(0, int(li) - a))
            bounds.append(starts[k] + (li - int(li)) * dur[a + k] - 0.15); at.append(a + k)
        bounds.append(e)
        out.append([(round(bounds[j], 3), round(bounds[j + 1], 3), at[j]) for j in range(n)])
        t = e
    return out


def estimate(lines):
    """Line lengths before the voice exists: about 14.5 characters per second (measured on the German voice of the
    old channel; measure again on the first videos of the English voice and correct this number)."""
    return {i: len(l) / 14.5 + 0.35 for i, l in enumerate(lines, 1)}


def edits_md(chapters, picks, times, text):
    """The list of edits for the owner (Vietnamese): shot number, time, line, picture, move, reason. The owner
    answers with e.g. "cảnh 5 đổi sang kiểu lùi ra"."""
    many = len(picks['chapters']) > 1
    rows, n = [], 0
    for ci, pc in enumerate(picks['chapters']):
        for j, p in enumerate(pc['pics']):
            n += 1
            s, e, li = times[ci][j]
            words = ' '.join(text.get(li, '').split())
            words = words if len(words) <= 60 else words[:57].rstrip() + '…'
            pic = ' + '.join(p['pair'][k]['img'] for k in ('left', 'right')) if 'pair' in p else p.get('img', '')
            m = p.get('move')
            kind = 'hai ảnh đóng khung' if 'pair' in p else f'{MOVES[m][0]} (`{m}`)' if m in MOVES else CUSTOM
            if p.get('fade') is not None and 'pair' not in p:
                kind += ', cắt thẳng' if p['fade'] == 0 else f', chuyển mờ {p["fade"]:g} giây'
            why = ' '.join(str(p.get('why', '')).split()).replace('|', '/')
            rows.append(f"| {n}{f' ({ci + 1}-{j + 1})' if many else ''} | {int(s // 60)}:{int(s % 60):02d} | {e - s:.0f} giây | "
                        f"{li}. {words.replace('|', '/')} | {pic} | {kind} | {why} |")
    legend = '; '.join(f'**{vi}** (`{k}`)' for k, (vi, _) in MOVES.items())
    return ('### Cách edit từng cảnh\n\n'
            '| Cảnh | Lúc | Dài | Câu đọc | Ảnh | Kiểu edit | Vì sao |\n|---|---|---|---|---|---|---|\n' + '\n'.join(rows) + '\n\n'
            f'Các kiểu edit có thể chọn: {legend}. Muốn đổi, bình luận ví dụ: "cảnh 5 đổi sang kiểu lùi ra".\n')
