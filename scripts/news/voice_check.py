#!/usr/bin/env python3
"""Check that the voice read every line right. Usage: voice_check.py <voice_dir> <check.md>

Each line_XX.mp3 is transcribed with Whisper (German); the transcript and the text that was sent to the voice are
compared word by word after normalising (lower case, no punctuation, ä/ö/ü/ß spelled out). A line is listed for
Claude to judge when a word differs by more than a small spelling variation (stretches where either side has
digits are ignored: Whisper writes numbers its own way). Whisper also mishears names and foreign words, so Claude
decides which entries are real misreadings. lines.json gets "heard", "score" and "diff".
"""
import difflib, json, os, re, sys
from faster_whisper import WhisperModel

vd, out = sys.argv[1], sys.argv[2]
rows = json.load(open(os.path.join(vd, 'lines.json'), encoding='utf-8'))


def words(t):
    t = t.lower()
    for a, b in (('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss')):
        t = t.replace(a, b)
    return re.findall(r'[a-z0-9àáâçèéêëíîñóôúû]+', t)


def close(a, b):
    """Same word apart from a spelling variation (Fluss/Fluß, compound written in two words)."""
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


m = WhisperModel('small', device='cpu', compute_type='int8')
bad = []
for r in rows:
    segs, _ = m.transcribe(os.path.join(vd, r['file']), language='de', beam_size=5)
    heard = ' '.join(s.text.strip() for s in segs).strip()
    a, b = words(r.get('tts') or r['text']), words(heard)
    sm = difflib.SequenceMatcher(None, a, b)
    diff = [(''.join(a[i1:i2]), ''.join(b[j1:j2])) for op, i1, i2, j1, j2 in sm.get_opcodes() if op != 'equal']
    r['heard'], r['score'] = heard, round(sm.ratio(), 2)
    r['diff'] = [f'{x or "∅"}→{y or "∅"}' for x, y in diff if not re.search(r'\d', x + y) and not close(x, y) and len(x + y) >= 3]
    if r['diff']:
        bad.append(r)
    print(r['i'], r['score'], heard, flush=True)
json.dump(rows, open(os.path.join(vd, 'lines.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
md = [f'# Kiểm tra giọng đọc ({len(rows)} câu, {len(bad)} câu cần xem)', '',
      'Whisper nghe lại từng câu và so từng từ. Câu nào có từ lệch được liệt kê: có thể giọng đọc sai, '
      'hoặc chỉ là Whisper nghe nhầm (hay gặp với tên riêng và từ nước ngoài).', '']
if bad:
    md += ['| Câu | Văn bản gửi đọc | Whisper nghe được | Chỗ lệch (đúng→nghe) |', '|---|---|---|---|']
    md += [f"| {r['i']} | {r.get('tts') or r['text']} | {r['heard']} | {', '.join(r['diff'])} |" for r in bad]
else:
    md += ['Không có câu nào đáng ngờ.']
open(out, 'w', encoding='utf-8').write('\n'.join(md) + '\n')
