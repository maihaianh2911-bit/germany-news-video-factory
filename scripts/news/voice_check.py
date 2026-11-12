#!/usr/bin/env python3
"""Check that the voice read every line right. Usage: voice_check.py <voice_dir> <check.md>

Each line_XX.mp3 is transcribed with Whisper (German); the transcript and the text that was sent to the voice are
compared word by word after normalising (lower case, no punctuation, ä/ö/ü/ß spelled out, and numbers written out
on both sides with num2words: "3,5 %" and "drei Komma fünf Prozent" are the same, "drei fünf Prozent" is not).
A line is listed for Claude to judge when a word differs: words of up to 5 letters must match exactly (ein/kein),
longer ones may differ only by a small spelling variation (Fluss/Fluß; Bundesverfassungsgericht/-verwaltungsgericht
is a difference). Whisper also mishears names and foreign words, so Claude decides which entries are real
misreadings. lines.json gets "heard", "score" and "diff".
"""
import difflib, json, os, re, sys
from num2words import num2words

MONTHS = 'Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember'
# 1.000 / 1.000,5 / 3,5 / 12 — and a following "." that makes it an ordinal ("am 12. November", "der 3. von 5")
NUM = re.compile(r'(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?(?:(\.)(?=\s+(?:[a-zäöüß]|\d|(?:' + MONTHS + r')\b)))?')
SYMBOLS = (('%', ' Prozent '), ('€', ' Euro '), ('§', ' Paragraf '), ('$', ' Dollar '), ('&', ' und '))


def spell_number(m):
    whole, frac, dot = m.group(1), m.group(2), m.group(3)
    n = int(whole.replace('.', ''))
    if dot and not frac:
        return ' ' + num2words(n, lang='de', to='ordinal') + ' '
    w = num2words(n, lang='de', to='year') if 1100 <= n <= 1999 and '.' not in whole and not frac else num2words(n, lang='de')
    if frac:   # spoken digit by digit: 3,25 → drei Komma zwei fünf
        w += ' Komma ' + ' '.join(num2words(int(d), lang='de') for d in frac)
    return ' ' + w + ' '


def words(t):
    for a, b in SYMBOLS:
        t = t.replace(a, b)
    t = NUM.sub(spell_number, t).lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        t = t.replace(a, b)
    out = []
    for w in re.findall(r'[a-z0-9àáâçèéêëíîñóôúû]+', t):
        w = re.sub(r'^ein(?=hundert|tausend)', '', w)   # (ein)hundert, (ein)tausend
        out.append('ein' if w == 'eins' else w)
    return out


def close(a, b):
    """Same word apart from a spelling variation or an ordinal ending (erste/ersten)."""
    if a == b:
        return True
    s, l = sorted((a, b), key=len)
    if l.startswith(s) and s.endswith('te') and l[len(s):] in ('n', 'r', 's', 'm'):
        return True
    if len(s) <= 5:   # short words carry meaning in one letter: ein/kein, mit/nit
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.9


def compare(sent, heard):
    """(similarity, ['sent→heard', …]) for the words that differ."""
    a, b = words(sent), words(heard)
    sm = difflib.SequenceMatcher(None, a, b)
    diff = [(''.join(a[i1:i2]), ''.join(b[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
    return round(sm.ratio(), 2), [f'{x or "∅"}→{y or "∅"}' for x, y in diff if not close(x, y) and len(x + y) >= 3]


def main():
    from faster_whisper import WhisperModel
    vd, out = sys.argv[1], sys.argv[2]
    rows = json.load(open(os.path.join(vd, 'lines.json'), encoding='utf-8'))
    m = WhisperModel('small', device='cpu', compute_type='int8')
    bad = []
    for r in rows:
        segs, _ = m.transcribe(os.path.join(vd, r['file']), language='de', beam_size=5)
        heard = ' '.join(s.text.strip() for s in segs).strip()
        r['heard'] = heard
        r['score'], r['diff'] = compare(r.get('tts') or r['text'], heard)
        if r['diff']:
            bad.append(r)
        print(r['i'], r['score'], heard, flush=True)
    json.dump(rows, open(os.path.join(vd, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    md = [f'# Kiểm tra giọng đọc ({len(rows)} câu, {len(bad)} câu cần xem)', '',
          'Whisper nghe lại từng câu và so từng từ (số được viết thành chữ ở cả hai bên). Câu nào có từ lệch được liệt kê: '
          'có thể giọng đọc sai, hoặc chỉ là Whisper nghe nhầm (hay gặp với tên riêng và từ nước ngoài).', '']
    if bad:
        md += ['| Câu | Văn bản gửi đọc | Whisper nghe được | Chỗ lệch (đúng→nghe) |', '|---|---|---|---|']
        md += [f"| {r['i']} | {r.get('tts') or r['text']} | {r['heard']} | {', '.join(r['diff'])} |" for r in bad]
    else:
        md += ['Không có câu nào đáng ngờ.']
    open(out, 'w', encoding='utf-8').write('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
