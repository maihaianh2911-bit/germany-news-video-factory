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
PAN = 0.085                 # a pan crosses at most this share of the panel per second
MAX_FADE = 1.5

# name → (Vietnamese label for the owner, what it looks like). Order = order of the table in AGENT_NEWS.md.
MOVES = {
    'tien-gan':   ('tiến gần', 'slow push-in towards the subject (about +3 % per second, +8…20 %)'),
    'chi-tiet':   ('soi chi tiết', 'from the whole picture strongly into one detail (+25…45 %)'),
    'lui-ra':     ('lùi ra', 'starts close on the subject and pulls back to the whole picture'),
    'luot-phai':  ('lướt sang phải', 'steady pan from left to right, no zoom change'),
    'luot-trai':  ('lướt sang trái', 'steady pan from right to left, no zoom change'),
    'nang-len':   ('nâng lên', 'tilt up: from the foot of the picture to its top'),
    'ha-xuong':   ('hạ xuống', 'tilt down: from the top of the picture to its foot'),
    'dung-yen':   ('đứng yên', 'held almost still (+3 %), the whole picture readable'),
    'troi-nhe':   ('trôi nhẹ', 'slightly closer, a small slow sideways drift that ends on the subject'),
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


def slide(w, h, dur, fx, fy, axis, sign):
    """A pan along one axis through the focus: zoomed in just enough to have room, at most PAN panel sizes per second."""
    z = 1.06
    while 1 - 2 * half(w, h, z)[axis] < 0.14 and z < 1.3:
        z += 0.02
    hv = half(w, h, z)[axis]; room = 1 - 2 * hv
    travel = min(room, PAN * max(dur, 1.0) * 2 * hv)      # share of the picture the centre moves
    f = (fx, fy)[axis]
    a = clamp(f - travel / 2, hv, 1 - hv - travel); b = a + travel
    if sign < 0: a, b = b, a
    return (cam(w, h, z, a, fy), cam(w, h, z, b, fy)) if axis == 0 else (cam(w, h, z, fx, a), cam(w, h, z, fx, b))


def expand(name, w, h, dur, focus=None):
    """(from, to) of move `name` for a prepared picture of w×h pixels shown for dur seconds, subject at focus (x, y)."""
    if name not in MOVES:
        raise ValueError(f'unknown move "{name}" — valid moves: {names()}')
    fx, fy = focus or FOCUS
    d = max(float(dur), 1.0)
    mid = lambda k: (0.5 + (fx - 0.5) * k, 0.5 + (fy - 0.5) * k)   # between the picture's centre (k=0) and the subject (k=1)
    if name == 'tien-gan':
        return cam(w, h, 1.0, fx, fy), cam(w, h, 1 + clamp(0.028 * d, 0.08, 0.20), fx, fy)
    if name == 'chi-tiet':
        return cam(w, h, 1.0, *mid(0.5)), cam(w, h, 1 + clamp(0.07 * d, 0.25, 0.45), fx, fy)
    if name == 'lui-ra':
        return cam(w, h, 1 + clamp(0.05 * d, 0.18, 0.32), fx, fy), cam(w, h, 1.0, *mid(0.5))
    if name == 'luot-phai': return slide(w, h, d, fx, fy, 0, 1)
    if name == 'luot-trai': return slide(w, h, d, fx, fy, 0, -1)
    if name == 'ha-xuong': return slide(w, h, d, fx, fy, 1, 1)
    if name == 'nang-len': return slide(w, h, d, fx, fy, 1, -1)
    if name == 'dung-yen':
        return cam(w, h, 1.0, fx, fy), cam(w, h, 1.03, fx, fy)
    # troi-nhe: a small drift that arrives on the subject, from the side with more room
    z = 1.1; hx = half(w, h, z)[0]
    step = min(1 - 2 * hx, 0.03 * d * 2 * hx)
    end = clamp(fx, hx, 1 - hx)
    start = end - step if end - step >= hx else min(1 - hx, end + step)
    return cam(w, h, z, start, fy), cam(w, h, z, end, fy)


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
    f = shot.get('focus')
    if f is not None and not (isinstance(f, (list, tuple)) and len(f) == 2 and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in f)):
        bad.append(f'{where}: "focus" phải là [x, y] trong khoảng 0–1')
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
        a, b = expand(shot['move'], w, h, dur, shot.get('focus'))
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
    """Line lengths before the voice exists: the German voice reads about 14.5 characters per second."""
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
